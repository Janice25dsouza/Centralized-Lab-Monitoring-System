# api/reports.py

import csv
import io
import json
from datetime import datetime

from pathlib import Path
from typing import Dict, List, Any
from collections import Counter

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak
)

from api.sessions import load_sessions


router = APIRouter(
    prefix="/reports",
    tags=["reports"]
)


# ============================================================
# Persistent warning history
# ============================================================

HISTORY_FILE = (
    Path(__file__).resolve().parent.parent
    / "database"
    / "warning_history.json"
)


def load_warning_history() -> List[Dict[str, Any]]:
    """
    Load all permanently stored warning events.
    """

    if not HISTORY_FILE.exists():
        return []

    try:
        with open(
            HISTORY_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if isinstance(data, dict):
            return data.get("events", [])

        return []

    except (json.JSONDecodeError, OSError):

        print(
            "[REPORTS] Could not read warning_history.json"
        )

        return []


# ============================================================
# Find session
# ============================================================

def find_session(session_id: str):

    sessions = load_sessions()

    for session in sessions:

        if session.get("session_id") == session_id:
            return session

    return None


# ============================================================
# Format timestamp
# ============================================================

def format_timestamp(timestamp):

    if not timestamp:
        return "N/A"

    try:

        return datetime.fromtimestamp(
            float(timestamp)
        ).strftime(
            "%d-%m-%Y %H:%M:%S"
        )

    except (ValueError, TypeError, OSError):

        return "N/A"


# ============================================================
# Calculate duration
# ============================================================

def calculate_duration(
    start_time,
    end_time
):

    if not start_time or not end_time:
        return "N/A"

    try:

        seconds = int(
            float(end_time) -
            float(start_time)
        )

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        remaining_seconds = seconds % 60

        if hours > 0:

            return (
                f"{hours}h "
                f"{minutes}m "
                f"{remaining_seconds}s"
            )

        if minutes > 0:

            return (
                f"{minutes}m "
                f"{remaining_seconds}s"
            )

        return f"{remaining_seconds}s"

    except (ValueError, TypeError):

        return "N/A"


# ============================================================
# Generate JSON session report
# ============================================================

@router.get("/session/{session_id}")
def generate_session_report(
    session_id: str
):

    session = find_session(session_id)

    if session is None:

        raise HTTPException(
            status_code=404,
            detail="Session not found."
        )

    # Only completed sessions
    if session.get("status") != "completed":

        raise HTTPException(
            status_code=400,
            detail={
                "message": "The lab session is still active.",
                "session_id": session_id,
                "status": session.get("status"),
                "hint": (
                    "End the lab session before "
                    "generating the final report."
                )
            }
        )

    history = load_warning_history()

    session_events = [
        event
        for event in history
        if event.get("session_id") == session_id
    ]

    total_violations = len(session_events)

    affected_pcs = sorted(
        {
            event.get("client_id")
            for event in session_events
            if event.get("client_id")
        }
    )

    violations_per_pc = Counter(
        event.get("client_id")
        for event in session_events
        if event.get("client_id")
    )

    violations_per_pc = dict(
        sorted(
            violations_per_pc.items()
        )
    )

    rule_counts = Counter(
        event.get(
            "matched_rule",
            "Unknown"
        )
        for event in session_events
    )

    rule_counts = dict(
        sorted(
            rule_counts.items(),
            key=lambda item: item[1],
            reverse=True
        )
    )

    timeline = sorted(
        session_events,
        key=lambda event: event.get(
            "recorded_at",
            event.get("timestamp", 0)
        )
    )

    return {
        "session": {
            "session_id": session.get(
                "session_id"
            ),
            "lab_name": session.get(
                "lab_name"
            ),
            "start_time": session.get(
                "start_time"
            ),
            "end_time": session.get(
                "end_time"
            ),
            "status": session.get(
                "status"
            )
        },

        "summary": {
            "total_violations": total_violations,
            "affected_pcs": len(
                affected_pcs
            ),
            "pc_list": affected_pcs
        },

        "violations_per_pc": violations_per_pc,

        "violations_by_rule": rule_counts,

        "timeline": timeline
    }


# ============================================================
# CSV EXPORT
# ============================================================

@router.get("/session/{session_id}/csv")
def export_session_csv(
    session_id: str
):

    session = find_session(session_id)

    if session is None:

        raise HTTPException(
            status_code=404,
            detail="Session not found."
        )

    if session.get("status") != "completed":

        raise HTTPException(
            status_code=400,
            detail={
                "message": "The lab session is still active.",
                "session_id": session_id,
                "status": session.get("status"),
                "hint": (
                    "End the lab session before "
                    "exporting the report."
                )
            }
        )

    history = load_warning_history()

    session_events = [
        event
        for event in history
        if event.get("session_id") == session_id
    ]

    output = io.StringIO()

    writer = csv.writer(output)

    writer.writerow([
        "Session ID",
        "Lab Name",
        "PC",
        "Window",
        "Matched Rule",
        "Client Timestamp",
        "Server Recorded At"
    ])

    sorted_events = sorted(
        session_events,
        key=lambda event: event.get(
            "recorded_at",
            event.get("timestamp", 0)
        )
    )

    for event in sorted_events:

        writer.writerow([
            session.get(
                "session_id",
                ""
            ),

            session.get(
                "lab_name",
                ""
            ),

            event.get(
                "client_id",
                ""
            ),

            event.get(
                "window",
                ""
            ),

            event.get(
                "matched_rule",
                ""
            ),

            event.get(
                "timestamp",
                ""
            ),

            event.get(
                "recorded_at",
                ""
            )
        ])

    output.seek(0)

    lab_name = session.get(
        "lab_name",
        "lab"
    )

    safe_lab_name = (
        str(lab_name)
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
    )

    filename = (
        f"lab_report_"
        f"{safe_lab_name}_"
        f"{session_id}.csv"
    )

    return StreamingResponse(
        iter([
            output.getvalue()
        ]),
        media_type="text/csv",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"'
            )
        }
    )


# ============================================================
# PDF EXPORT
# ============================================================

@router.get("/session/{session_id}/pdf")
def export_session_pdf(
    session_id: str
):

    # --------------------------------------------------------
    # Find session
    # --------------------------------------------------------

    session = find_session(session_id)

    if session is None:

        raise HTTPException(
            status_code=404,
            detail="Session not found."
        )

    # --------------------------------------------------------
    # Only completed sessions
    # --------------------------------------------------------

    if session.get("status") != "completed":

        raise HTTPException(
            status_code=400,
            detail={
                "message": "The lab session is still active.",
                "session_id": session_id,
                "status": session.get("status"),
                "hint": (
                    "End the lab session before "
                    "exporting the report."
                )
            }
        )

    # --------------------------------------------------------
    # Load warning history
    # --------------------------------------------------------

    history = load_warning_history()

    session_events = [
        event
        for event in history
        if event.get("session_id") == session_id
    ]

    # --------------------------------------------------------
    # Sort events
    # --------------------------------------------------------

    sorted_events = sorted(
        session_events,
        key=lambda event: event.get(
            "recorded_at",
            event.get("timestamp", 0)
        )
    )

    # --------------------------------------------------------
    # Calculate summary
    # --------------------------------------------------------

    total_violations = len(
        sorted_events
    )

    affected_pcs = sorted(
        {
            event.get("client_id")
            for event in sorted_events
            if event.get("client_id")
        }
    )

    violations_per_pc = Counter(
        event.get("client_id")
        for event in sorted_events
        if event.get("client_id")
    )

    violations_per_pc = dict(
        sorted(
            violations_per_pc.items()
        )
    )

    violations_by_rule = Counter(
        event.get(
            "matched_rule",
            "Unknown"
        )
        for event in sorted_events
    )

    violations_by_rule = dict(
        sorted(
            violations_by_rule.items(),
            key=lambda item: item[1],
            reverse=True
        )
    )

    # --------------------------------------------------------
    # Create PDF in memory
    # --------------------------------------------------------

    pdf_buffer = io.BytesIO()

    document = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm
    )

    # --------------------------------------------------------
    # Styles
    # --------------------------------------------------------

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=20,
        spaceAfter=8
    )

    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontSize=10,
        spaceAfter=15
    )

    heading_style = ParagraphStyle(
        "ReportHeading",
        parent=styles["Heading2"],
        fontSize=13,
        spaceBefore=12,
        spaceAfter=8
    )

    normal_style = ParagraphStyle(
        "ReportNormal",
        parent=styles["Normal"],
        fontSize=9,
        leading=12
    )

    # --------------------------------------------------------
    # Story
    # --------------------------------------------------------

    story = []

    # --------------------------------------------------------
    # Title
    # --------------------------------------------------------

    story.append(
        Paragraph(
            "Lab Monitoring Report",
            title_style
        )
    )

    story.append(
        Paragraph(
            "Computer Laboratory Monitoring System",
            subtitle_style
        )
    )

    # --------------------------------------------------------
    # Session information
    # --------------------------------------------------------

    story.append(
        Paragraph(
            "Session Information",
            heading_style
        )
    )

    session_data = [
        [
            "Lab Name",
            str(
                session.get(
                    "lab_name",
                    "N/A"
                )
            )
        ],

        [
            "Session ID",
            str(
                session.get(
                    "session_id",
                    "N/A"
                )
            )
        ],

        [
            "Status",
            str(
                session.get(
                    "status",
                    "N/A"
                )
            ).capitalize()
        ],

        [
            "Start Time",
            format_timestamp(
                session.get(
                    "start_time"
                )
            )
        ],

        [
            "End Time",
            format_timestamp(
                session.get(
                    "end_time"
                )
            )
        ],

        [
            "Duration",
            calculate_duration(
                session.get(
                    "start_time"
                ),
                session.get(
                    "end_time"
                )
            )
        ]
    ]

    session_table = Table(
        session_data,
        colWidths=[
            45 * mm,
            125 * mm
        ]
    )

    session_table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (0, -1),
                colors.lightgrey
            ),

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.grey
            ),

            (
                "FONTNAME",
                (0, 0),
                (0, -1),
                "Helvetica-Bold"
            ),

            (
                "FONTNAME",
                (1, 0),
                (1, -1),
                "Helvetica"
            ),

            (
                "FONTSIZE",
                (0, 0),
                (-1, -1),
                8
            ),

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "TOP"
            ),

            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                6
            ),

            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                6
            ),

            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                6
            ),

            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                6
            )
        ])
    )

    story.append(
        session_table
    )

    story.append(
        Spacer(
            1,
            8
        )
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    story.append(
        Paragraph(
            "Summary",
            heading_style
        )
    )

    summary_data = [
        [
            "Total Violations",
            str(total_violations)
        ],

        [
            "Affected PCs",
            str(len(affected_pcs))
        ]
    ]

    summary_table = Table(
        summary_data,
        colWidths=[
            65 * mm,
            105 * mm
        ]
    )

    summary_table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (0, -1),
                colors.lightgrey
            ),

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.grey
            ),

            (
                "FONTNAME",
                (0, 0),
                (0, -1),
                "Helvetica-Bold"
            ),

            (
                "FONTSIZE",
                (0, 0),
                (-1, -1),
                9
            ),

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE"
            )
        ])
    )

    story.append(
        summary_table
    )

    # --------------------------------------------------------
    # Violations per PC
    # --------------------------------------------------------

    story.append(
        Paragraph(
            "Violations Per PC",
            heading_style
        )
    )

    pc_table_data = [
        [
            "PC",
            "Violations"
        ]
    ]

    if violations_per_pc:

        for pc, count in violations_per_pc.items():

            pc_table_data.append([
                str(pc),
                str(count)
            ])

    else:

        pc_table_data.append([
            "No violations",
            "0"
        ])

    pc_table = Table(
        pc_table_data,
        colWidths=[
            120 * mm,
            50 * mm
        ],
        repeatRows=1
    )

    pc_table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.lightgrey
            ),

            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold"
            ),

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.grey
            ),

            (
                "FONTSIZE",
                (0, 0),
                (-1, -1),
                8
            ),

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE"
            )
        ])
    )

    story.append(
        pc_table
    )

    # --------------------------------------------------------
    # Violations by rule
    # --------------------------------------------------------

    story.append(
        Paragraph(
            "Violations By Rule",
            heading_style
        )
    )

    rule_table_data = [
        [
            "Matched Rule",
            "Count"
        ]
    ]

    if violations_by_rule:

        for rule, count in violations_by_rule.items():

            rule_table_data.append([
                str(rule),
                str(count)
            ])

    else:

        rule_table_data.append([
            "No violations",
            "0"
        ])

    rule_table = Table(
        rule_table_data,
        colWidths=[
            120 * mm,
            50 * mm
        ],
        repeatRows=1
    )

    rule_table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.lightgrey
            ),

            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold"
            ),

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.grey
            ),

            (
                "FONTSIZE",
                (0, 0),
                (-1, -1),
                8
            ),

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "TOP"
            )
        ])
    )

    story.append(
        rule_table
    )

    # --------------------------------------------------------
    # Detailed timeline
    # --------------------------------------------------------

    story.append(
        Paragraph(
            "Violation Timeline",
            heading_style
        )
    )

    timeline_data = [
        [
            "Time",
            "PC",
            "Window / Application",
            "Matched Rule"
        ]
    ]

    if sorted_events:

        for event in sorted_events:

            timeline_data.append([
                format_timestamp(
                    event.get(
                        "recorded_at",
                        event.get(
                            "timestamp"
                        )
                    )
                ),

                str(
                    event.get(
                        "client_id",
                        ""
                    )
                ),

                str(
                    event.get(
                        "window",
                        ""
                    )
                ),

                str(
                    event.get(
                        "matched_rule",
                        ""
                    )
                )
            ])

    else:

        timeline_data.append([
            "—",
            "—",
            "No violations recorded",
            "—"
        ])

    timeline_table = Table(
        timeline_data,
        colWidths=[
            32 * mm,
            25 * mm,
            65 * mm,
            48 * mm
        ],
        repeatRows=1
    )

    timeline_table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.lightgrey
            ),

            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold"
            ),

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.grey
            ),

            (
                "FONTSIZE",
                (0, 0),
                (-1, -1),
                7
            ),

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "TOP"
            ),

            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                4
            ),

            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                4
            ),

            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                4
            ),

            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                4
            )
        ])
    )

    story.append(
        timeline_table
    )

    # --------------------------------------------------------
    # Footer note
    # --------------------------------------------------------

    story.append(
        Spacer(
            1,
            12
        )
    )

    story.append(
        Paragraph(
            "This report was generated by the "
            "Lab Monitoring System.",
            normal_style
        )
    )

    # --------------------------------------------------------
    # Build PDF
    # --------------------------------------------------------

    document.build(
        story
    )

    pdf_buffer.seek(0)

    # --------------------------------------------------------
    # Filename
    # --------------------------------------------------------

    lab_name = session.get(
        "lab_name",
        "lab"
    )

    safe_lab_name = (
        str(lab_name)
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
    )

    filename = (
        f"lab_report_"
        f"{safe_lab_name}_"
        f"{session_id}.pdf"
    )

    # --------------------------------------------------------
    # Return PDF
    # --------------------------------------------------------

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"'
            )
        }
    )