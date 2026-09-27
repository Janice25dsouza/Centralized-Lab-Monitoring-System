# uvicorn main:app --reload
# uvicorn main:app --host 0.0.0.0 --port 8000

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import clients, commands, logs, lab_config, sessions, reports
from discovery import start_discovery, stop_discovery


@asynccontextmanager
async def lifespan(app: FastAPI):

    # Start Zeroconf server advertisement
    await start_discovery()

    yield

    # Stop Zeroconf server advertisement
    await stop_discovery()


app = FastAPI(lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(clients.router)
app.include_router(commands.router)
app.include_router(logs.router)
app.include_router(lab_config.router)
app.include_router(sessions.router)
app.include_router(reports.router)


@app.get("/")
def home():
    return {"message": "Server running"}