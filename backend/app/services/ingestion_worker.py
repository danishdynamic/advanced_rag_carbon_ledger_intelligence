import logging
import uuid
import io
import asyncpg
from google import genai
from google.genai import types
from app.config import settings
from app.services.search import compliance_search

logger = logging.getLogger("carbon_ledger.ingestion_worker")

def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> list[str]:
    """Splits plain text into sliding window semantic fragments."""
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk_words = words[i:i + chunk_size]
        chunks.append(" ".join(chunk_words))
        if i + chunk_size >= len(words):
            break
        i += (chunk_size - overlap)
    return chunks

async def process_document_task(task_id: uuid.UUID, file_name: str, file_bytes: bytes):
    """
    Polymorphic async worker thread.
    Uses local decoding for text, and Gemini Multimodal Vision for PDFs 
    to extract text, transcribe tables, and interpret visual charts/graphs.
    """
    conn = await asyncpg.connect(settings.PRIMARY_DB_URL)
    # Instantiate a standalone GenAI client for the background worker lifecycle
    ai_client = genai.Client()
    
    try:
        await conn.execute(
            "UPDATE ingestion_tasks SET status = 'processing', updated_at = CURRENT_TIMESTAMP WHERE task_id = $1;",
            task_id
        )
        
        full_extracted_text = ""
        lower_name = file_name.lower()

        # 1. Plain Text Routing
        if lower_name.endswith('.txt'):
            logger.info(f"Routing task {task_id} to Plain Text Decoder...")
            full_extracted_text = file_bytes.decode("utf-8", errors="ignore")

        # 2. Multimodal PDF Vision Routing (Handles Text, Scan OCR, and Charts)
        elif lower_name.endswith('.pdf'):
            logger.info(f"Routing task {task_id} to Gemini Multimodal Vision Engine...")
            
            # Upload the raw binary stream securely to the temporary Gemini Files API storage
            pdf_buffer = io.BytesIO(file_bytes)
            uploaded_file = ai_client.files.upload(
                file=pdf_buffer,
                config=types.UploadFileConfig(mime_type="application/pdf")
            )
            
            logger.info(f"PDF successfully staged in Gemini File API. Name: {uploaded_file.name}")

            # Instruct the vision model to extract layout context along with deep chart analysis
            parsing_prompt = """
            You are an advanced document parsing engine. Extract all content from this compliance document with perfect structural fidelity.
            
            CRITICAL RULES:
            1. Transcribe all text paragraphs exactly as written.
            2. If you encounter charts, data graphs, or visual diagrams, analyze the pixels and write an exhaustive textual description of the trends, data points, and values shown.
            3. If you encounter tables, extract and format them completely into clean Markdown tables.
            
            Output the raw extracted text and visual summaries directly without introducing meta-commentary.
            """

            # Run the visual parsing pass
            response = ai_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[uploaded_file, parsing_prompt]
            )
            
            full_extracted_text = response.text if response.text else ""
            
            # Clean up the file from Gemini cloud storage immediately after processing
            try:
                if uploaded_file.name:  # ◄— Type guard guarantees 'str' type to Pylance
                    ai_client.files.delete(name=uploaded_file.name)
                    logger.info(f"Cleaned up remote staging file: {uploaded_file.name}")
                else:
                    logger.warning("Staged file identifier missing; skipping remote cleanup payload.")
            except Exception as clean_err:
                logger.warning(f"Non-blocking failure cleaning up staged Gemini file: {str(clean_err)}")

        # 3. Safety Check
        if not full_extracted_text.strip():
            raise ValueError("Vision extraction pass returned an unparsable or completely empty text payload.")

        # 4. Process chunks and save to vector database
        chunks = chunk_text(full_extracted_text)
        
        await conn.execute(
            "UPDATE ingestion_tasks SET total_chunks = $2 WHERE task_id = $1;",
            task_id, len(chunks)
        )

        inferred_framework = file_name.split(".")[0].upper()[:15]

        for idx, chunk in enumerate(chunks):
            embedding_vector = await compliance_search._generate_embedding(chunk)
            vector_str = f"[{','.join(map(str, embedding_vector))}]"
            
            await conn.execute(
                """
                INSERT INTO compliance_documents (framework_name, section_identifier, raw_text_chunk, metadata_tags, embedding_vector)
                VALUES ($1, $2, $3, $4::jsonb, $5::vector);
                """,
                inferred_framework,
                f"Vision Ingest Segment - Block {idx + 1}",
                chunk,
                "{}",
                vector_str
            )

        await conn.execute(
            "UPDATE ingestion_tasks SET status = 'completed', updated_at = CURRENT_TIMESTAMP WHERE task_id = $1;",
            task_id
        )
        logger.info(f"Multi-format visual ingestion task {task_id} successfully closed out.")

    except Exception as e:
        logger.error(f"Multi-format visual worker execution failed on job {task_id}: {str(e)}")
        await conn.execute(
            "UPDATE ingestion_tasks SET status = 'failed', error_message = $2, updated_at = CURRENT_TIMESTAMP WHERE task_id = $1;",
            task_id, str(e)
        )
    finally:
        await conn.close()