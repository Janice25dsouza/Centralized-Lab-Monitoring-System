from fastapi import APIRouter
from pydantic import BaseModel

from services.lab_config import get_config, save_config


router = APIRouter()


class LabPC(BaseModel):
    client_id: str
    pc_name: str
    row: int
    column: int


@router.get("/lab-config")
def get_lab_config():
    return get_config()


@router.post("/lab-config/pcs")
def register_lab_pc(pc: LabPC):
    config = get_config()

    # Check whether this client is already registered
    for existing_pc in config["pcs"]:
        if existing_pc["client_id"] == pc.client_id:
            return {
                "status": "error",
                "message": "This client_id is already registered."
            }

    # Check physical position
    rows = config["lab"]["rows"]
    columns = config["lab"]["columns"]

    if pc.row < 1 or pc.row > rows:
        return {
            "status": "error",
            "message": f"Row must be between 1 and {rows}."
        }

    if pc.column < 1 or pc.column > columns:
        return {
            "status": "error",
            "message": f"Column must be between 1 and {columns}."
        }

    # Make sure another PC isn't already occupying this position
    for existing_pc in config["pcs"]:
        if (
            existing_pc["row"] == pc.row
            and existing_pc["column"] == pc.column
        ):
            return {
                "status": "error",
                "message": "This physical position is already occupied."
            }

    config["pcs"].append(pc.model_dump())
    save_config(config)

    return {
        "status": "registered",
        "pc": pc.model_dump()
    }


@router.put("/lab-config/pcs/{client_id}")
def update_lab_pc(client_id: str, pc: LabPC):
    config = get_config()

    # Make sure the URL client_id and body client_id match
    if client_id != pc.client_id:
        return {
            "status": "error",
            "message": "client_id in URL and request body must match."
        }

    rows = config["lab"]["rows"]
    columns = config["lab"]["columns"]

    if pc.row < 1 or pc.row > rows:
        return {
            "status": "error",
            "message": f"Row must be between 1 and {rows}."
        }

    if pc.column < 1 or pc.column > columns:
        return {
            "status": "error",
            "message": f"Column must be between 1 and {columns}."
        }

    for index, existing_pc in enumerate(config["pcs"]):

        if existing_pc["client_id"] == client_id:

            # Make sure the new position isn't occupied by another PC
            for other_pc in config["pcs"]:
                if other_pc["client_id"] == client_id:
                    continue

                if (
                    other_pc["row"] == pc.row
                    and other_pc["column"] == pc.column
                ):
                    return {
                        "status": "error",
                        "message": "This physical position is already occupied."
                    }

            config["pcs"][index] = pc.model_dump()
            save_config(config)

            return {
                "status": "updated",
                "pc": pc.model_dump()
            }

    return {
        "status": "error",
        "message": "PC not found."
    }


@router.delete("/lab-config/pcs/{client_id}")
def delete_lab_pc(client_id: str):
    config = get_config()

    for index, existing_pc in enumerate(config["pcs"]):

        if existing_pc["client_id"] == client_id:
            deleted_pc = config["pcs"].pop(index)

            save_config(config)

            return {
                "status": "deleted",
                "pc": deleted_pc
            }

    return {
        "status": "error",
        "message": "PC not found."
    }

@router.put("/lab-config")
def update_lab_config(lab: dict):
    config = get_config()

    new_name = lab.get("name", config["lab"]["name"])
    new_rows = lab.get("rows", config["lab"]["rows"])
    new_columns = lab.get("columns", config["lab"]["columns"])

    # Check that the new dimensions are valid
    if new_rows < 1 or new_columns < 1:
        return {
            "status": "error",
            "message": "Rows and columns must be at least 1."
        }

    # Make sure existing PCs still fit inside the new grid
    for pc in config["pcs"]:
        if pc["row"] > new_rows or pc["column"] > new_columns:
            return {
                "status": "error",
                "message": (
                    f"Cannot resize the lab because {pc['pc_name']} "
                    f"is currently at row {pc['row']}, column {pc['column']}."
                )
            }

    config["lab"] = {
        "name": new_name,
        "rows": new_rows,
        "columns": new_columns
    }

    save_config(config)

    return {
        "status": "updated",
        "lab": config["lab"]
    }