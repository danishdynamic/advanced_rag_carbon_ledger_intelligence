import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Header
from pydantic import BaseModel, Field
import asyncpg
from datetime import datetime


from app.database import get_write_db, get_read_db, register_user_write
from app.services.ingestion_worker import process_document_task

logger = logging.getLogger("carbon_ledger.routers.documents")
router = APIRouter(prefix="/api/documents", tags=["Document Lifecycle Execution"])

# --- Pydantic Structural Schemas ---

class TaskStatusResponse(BaseModel):
    task_id: uuid.UUID
    file_name: str
    status: str = Field(..., description="pending, processing, completed, or failed")
    total_chunks: int
    error_message: str | None = None
    updated_at: datetime

class IngestionReceipt(BaseModel):
    task_id: uuid.UUID
    file_name: str
    status: str
    message: str

# --- Endpoints ---

@router.post("/upload", status_code=202, response_model=IngestionReceipt)
async def upload_compliance_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db_conn: asyncpg.Connection = Depends(get_write_db),
    x_user_id: str = Header(default="anonymous_client")
):
    """
    Accepts both plain text (.txt) and binary PDF (.pdf) documents,
    logging an ingestion ticket and streaming bytes to the background parser.
    """
    if not file.filename or not file.filename.lower().endswith(('.pdf', '.txt')):
        raise HTTPException(
            status_code=400, 
            detail="Unsupported format. The engine currently accepts only .pdf and .txt files."
        )

    try:
        file_bytes = await file.read()
        task_id = uuid.uuid4()
        task_id_str: uuid.UUID = str(task_id)  # type: ignore[assignment]
        
        # Write initial task entry to primary cluster
        await db_conn.execute(
            """
            INSERT INTO ingestion_tasks (task_id, file_name, status)
            VALUES ($1, $2, 'pending');
            """,
            task_id_str, file.filename
        )

        # Track write sequence to protect against replication lag
        register_user_write(x_user_id)

        # Dispatch background worker task for pure pgvector RAG processing
        background_tasks.add_task(
            process_document_task, 
            task_id, 
            file.filename, 
            file_bytes
        )

        return IngestionReceipt(
            task_id=task_id,
            file_name=file.filename,
            status="pending",
            message="Document successfully queued for background parsing and vectorization."
        )

    except Exception as e:
        logger.error(f"Failed to initialize file upload pipeline: {str(e)}")
        raise HTTPException(status_code=500, detail="Document ingestion scheduling initialization failed.")


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def fetch_ingestion_task_status(
    task_id: uuid.UUID,
    db_conn: asyncpg.Connection = Depends(get_read_db)
):
    """Fetches the state of an ingestion job from the read-replica database pool."""
    task_id_str: uuid.UUID = str(task_id)  # type: ignore[assignment]

    row = await db_conn.fetchrow(
        """
        SELECT task_id, file_name, status, total_chunks, error_message, updated_at
        FROM ingestion_tasks
        WHERE task_id = $1;
        """,
        task_id_str
    )
    
    if not row:
        raise HTTPException(status_code=404, detail="Requested ingestion processing token not found.")
        
    return TaskStatusResponse(**dict(row))