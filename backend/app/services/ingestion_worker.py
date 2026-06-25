import logging
import uuid
import io
import json
import asyncpg
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from app.config import settings
from app.services.search import compliance_search
from .quota_manager import check_and_increment_quota

logger = logging.getLogger("carbon_ledger.ingestion_worker")
genai_client = genai.Client()


# --- Graph Extraction Contract Schemas ---
class ExtractedEntity(BaseModel):
    name: str
    type: str  # 'FRAMEWORK', 'FACILITY', 'METRIC', 'ORGANIZATION'
    description: str


class ExtractedRelationship(BaseModel):
    source_node: str
    target_node: str
    predicate: str  # 'GOVERNS', 'EMITS', 'ENFORCES', 'REDUCES'
    context_excerpt: str


class KnowledgeGraphPayload(BaseModel):
    entities: list[ExtractedEntity]
    relationships: list[ExtractedRelationship]


# --- Parent-Child Granular Chunking Utilities ---
def chunk_to_parent_blocks(
    text: str, chunk_size: int = 1200, overlap: int = 200
) -> list[str]:
    """Generates large context nodes to preserve overall textual narrative flow."""
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk_words = words[i : i + chunk_size]
        chunks.append(" ".join(chunk_words))
        if i + chunk_size >= len(words):
            break
        i += chunk_size - overlap
    return chunks


def chunk_to_child_blocks(
    parent_text: str, chunk_size: int = 250, overlap: int = 50
) -> list[str]:
    """Generates hyper-focused sub-segments optimized for sharp semantic embedding vector spaces."""
    words = parent_text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk_words = words[i : i + chunk_size]
        chunks.append(" ".join(chunk_words))
        if i + chunk_size >= len(words):
            break
        i += chunk_size - overlap
    return chunks


# --- Graph-RAG Topology Processing ---
async def extract_and_store_graph_topology(
    text_chunk: str, db_conn: asyncpg.Connection
):
    """
    🧠 GRAPH-RAG PIPELINE STEP: Uses structured LLM synthesis to extract standard topology
    nodes and map interconnectivity layers straight to PostgreSQL storage nodes.
    """
    prompt = f"""
    Analyze this corporate ESG document fragment and extract semantic entities and their direct operational links.
    TEXT CHUNK:
    {text_chunk}
    """
    try:
        response = genai_client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=KnowledgeGraphPayload,
                temperature=0.1,
            ),
        )

        raw_json = response.text if response.text else "{}"

        graph_data = KnowledgeGraphPayload.model_validate_json(raw_json)

        for entity in graph_data.entities:
            await db_conn.execute(
                """
                INSERT INTO graph_entities (entity_name, entity_type, description)
                VALUES ($1, $2, $3)
                ON CONFLICT (entity_name) DO UPDATE SET description = EXCLUDED.description;
            """,
                entity.name,
                entity.type.upper(),
                entity.description,
            )

        for rel in graph_data.relationships:
            await db_conn.execute(
                """
                INSERT INTO graph_relationships (source_entity_id, target_entity_id, predicate, context_summary)
                VALUES (
                    (SELECT entity_id FROM graph_entities WHERE entity_name = $1),
                    (SELECT entity_id FROM graph_entities WHERE entity_name = $2),
                    $3, $4
                ) ON CONFLICT DO NOTHING;
            """,
                rel.source_node,
                rel.target_node,
                rel.predicate.upper(),
                rel.context_excerpt,
            )
    except Exception as e:
        logger.warning(f"Graph extraction non-blocking skip on trace: {str(e)}")


# --- Core Process Execution Worker Task ---
async def process_document_task(task_id: uuid.UUID, file_name: str, file_bytes: bytes):
    task_id_str = str(task_id)
    conn = await asyncpg.connect(settings.PRIMARY_DB_URL)

    ai_client = genai.Client(
        http_options=types.HttpOptions(
            timeout=1200 * 1000,
            retry_options=types.HttpRetryOptions(
                initial_delay=2.0,
                attempts=5,
                exp_base=2,
                http_status_codes=[429, 500, 502, 503, 504],
            ),
        )
    )

    try:
        await conn.execute(
            "UPDATE ingestion_tasks SET status = 'processing', updated_at = CURRENT_TIMESTAMP WHERE task_id = $1;",
            task_id_str,
        )

        full_extracted_text = ""
        lower_name = file_name.lower()

        if lower_name.endswith(".txt"):
            logger.info(f"Routing task {task_id} to Plain Text Decoder...")
            full_extracted_text = file_bytes.decode("utf-8", errors="ignore")

        elif lower_name.endswith(".pdf"):
            logger.info(f"Routing task {task_id} to Gemini Multimodal Vision Engine...")
            pdf_buffer = io.BytesIO(file_bytes)
            uploaded_file = ai_client.files.upload(
                file=pdf_buffer,
                config=types.UploadFileConfig(mime_type="application/pdf"),
            )

            parsing_prompt = "Extract all text content from this compliance document with perfect structural fidelity."
            await check_and_increment_quota(conn)

            response = await ai_client.aio.models.generate_content(
                model="gemini-3.1-flash-lite", contents=[uploaded_file, parsing_prompt]
            )
            full_extracted_text = response.text if response.text else ""

            try:
                if uploaded_file.name:
                    ai_client.files.delete(name=uploaded_file.name)
            except Exception as clean_err:
                logger.warning(f"Non-blocking file cleanup failure: {str(clean_err)}")

        if not full_extracted_text.strip():
            raise ValueError(
                "Extraction pass returned an unparsable or completely empty text payload."
            )

        # --- PHASE 3: PARENT-CHILD CHUNKING & GRAPH MATRIX INGESTION ---
        parent_blocks = chunk_to_parent_blocks(full_extracted_text)
        inferred_framework = file_name.split(".")[0].upper()[:15]

        total_child_chunks_written = 0

        for p_idx, parent_text in enumerate(parent_blocks):
            # 💡 1. Store the Broad Parent Context Node
            parent_id = await conn.fetchval(
                """
                INSERT INTO compliance_documents (framework_name, section_identifier, raw_text_chunk, metadata_tags, embedding_vector)
                VALUES ($1, $2, $3, $4::jsonb, NULL)
                RETURNING id;
                """,
                inferred_framework,
                f"Parent-Block-{p_idx + 1}",
                parent_text,
                json.dumps({"is_parent": True}),
            )

            # 💡 2. Dynamic Graph-RAG Pipeline Integration Check
            await extract_and_store_graph_topology(parent_text, conn)

            # 💡 3. Parse and Insert Precise Child Chunks mapped to Parent ID
            child_blocks = chunk_to_child_blocks(parent_text)
            for c_idx, child_text in enumerate(child_blocks):
                embedding_vector = await compliance_search._generate_embedding(
                    child_text
                )
                vector_str = f"[{','.join(map(str, embedding_vector))}]"

                await conn.execute(
                    """
                    INSERT INTO compliance_documents (framework_name, section_identifier, raw_text_chunk, metadata_tags, embedding_vector)
                    VALUES ($1, $2, $3, $4::jsonb, $5::vector);
                    """,
                    inferred_framework,
                    f"Child-Segment-{p_idx + 1}-{c_idx + 1}",
                    child_text,
                    json.dumps({"parent_reference_id": parent_id, "is_child": True}),
                    vector_str,
                )
                total_child_chunks_written += 1

        await conn.execute(
            "UPDATE ingestion_tasks SET status = 'completed', total_chunks = $2, updated_at = CURRENT_TIMESTAMP WHERE task_id = $1;",
            task_id_str,
            total_child_chunks_written,
        )
        logger.info(
            f"Advanced Graph-RAG and Parent-Child task {task_id} successfully finalized."
        )

    except Exception as e:
        logger.error(f"Execution failed on job {task_id}: {str(e)}")
        await conn.execute(
            "UPDATE ingestion_tasks SET status = 'failed', error_message = $2, updated_at = CURRENT_TIMESTAMP WHERE task_id = $1;",
            task_id_str,
            str(e),
        )
    finally:
        await conn.close()
