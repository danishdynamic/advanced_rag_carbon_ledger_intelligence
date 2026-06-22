import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import db_manager
from app.routers import compliance

# Configure logging baseline
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("carbon_ledger")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup Phase: Trigger pool initializations before accepting HTTP traffic
    await db_manager.connect()
    yield
    # Shutdown Phase: Safe termination when the process receives a SIGTERM signal
    await db_manager.disconnect()

app = FastAPI(
    title="Carbon Ledger Intelligence Core",
    version="2.0.0",
    lifespan=lifespan
)

# Permit local React web client configurations
origins = [
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(compliance.router)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "cluster_routing": "active"}