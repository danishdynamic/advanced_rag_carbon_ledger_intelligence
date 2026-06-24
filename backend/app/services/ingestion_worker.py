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

class CorporateClimateMetrics(BaseModel):
    facility_name: str = Field(description="The primary corporate entity or specific facility/plant name discussed in the document.")
    annual_co2_emissions_tons: float = Field(description="The numeric annual carbon or CO2 emissions in metric tons. Default to 0.0 if not found.")
    regulatory_framework: str = Field(description="The governing framework mentioned (e.g., EU-ETS, CCA, local compliance). Default to 'Baseline'.")

def chunk_text(text: str, chunk_size: int = 800, overlap: int = 150) -> list[str]:
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
            )
        )
    )
    
    try:
        await conn.execute(
            "UPDATE ingestion_tasks SET status = 'processing', updated_at = CURRENT_TIMESTAMP WHERE task_id = $1;",
            task_id_str
        )
        
        full_extracted_text = ""
        lower_name = file_name.lower()

        # --- PHASE 1: PLAIN TEXT INGESTION ---
        if lower_name.endswith('.txt'):
            logger.info(f"Routing task {task_id} to Plain Text Decoder...")
            full_extracted_text = file_bytes.decode("utf-8", errors="ignore")

        # --- PHASE 2: MULTIMODAL PDF PARSING (GEMINI VISION) ---
        elif lower_name.endswith('.pdf'):
            logger.info(f"Routing task {task_id} to Gemini Multimodal Vision Engine...")
            
            pdf_buffer = io.BytesIO(file_bytes)
            uploaded_file = ai_client.files.upload(
                file=pdf_buffer,
                config=types.UploadFileConfig(mime_type="application/pdf")
            )
            
            logger.info(f"PDF successfully staged in Gemini File API. Name: {uploaded_file.name}")

            parsing_prompt = """
            You are an advanced document parsing engine. Extract all content from this compliance document with perfect structural fidelity.
            ...
            """

            # 🛡️ Quota Check #1: Right before vision extraction
            await check_and_increment_quota(conn)

            response = await ai_client.aio.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=[uploaded_file, parsing_prompt]
            )
            
            full_extracted_text = response.text if response.text else ""
            
            try:
                if uploaded_file.name:
                    ai_client.files.delete(name=uploaded_file.name)
                    logger.info(f"Cleaned up remote staging file: {uploaded_file.name}")
            except Exception as clean_err:
                logger.warning(f"Non-blocking failure cleaning up staged Gemini file: {str(clean_err)}")

        # --- PHASE 3: SAFETY GUARD & ANALYTICS CALCULATION ---
        if not full_extracted_text.strip():
            raise ValueError("Vision extraction pass returned an unparsable or completely empty text payload.")

        if lower_name.endswith('.pdf'):
            logger.info(f"Executing structured data extraction pass for task {task_id}...")
            
            analysis_prompt = f"""
            Analyze the following extracted document text and extract the specific environmental parameters requested in the output schema.
            
            Document Text:
            {full_extracted_text}
            """
            
            # 🛡️ Quota Check #2: Right before structural data generation
            await check_and_increment_quota(conn)
            
            # ⚡ Optimized: Converted from blocking sync client to async .aio client
            structured_response = await ai_client.aio.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=analysis_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=CorporateClimateMetrics,
                ),
            )

            raw_json = structured_response.text
            if not raw_json:
                raise ValueError("Gemini structured extraction returned an empty or missing text payload.")
            
            metrics = json.loads(raw_json)
            
            facility = metrics.get("facility_name", f"Unknown Facility ({file_name})")
            emissions = float(metrics.get("annual_co2_emissions_tons", 0.0))
            framework = metrics.get("regulatory_framework", "Baseline")
            
            carbon_price_baseline = 90.00
            projected_liability = emissions * carbon_price_baseline
            risk_level = "high" if projected_liability > 50000.0 else "low"
            scenario_meta = f"Gemini Parsing Pass - Framework: {framework}"
            
            logger.info(f"Writing calculated risk variables to climate_risk_assessments for facility: {facility}")
            await conn.execute(
                """
                INSERT INTO climate_risk_assessments (assessment_id, facility_name, projected_tax_liability, risk_level, scenario_type)
                VALUES (gen_random_uuid(), $1, $2, $3, $4);
                """,
                facility, projected_liability, risk_level, scenario_meta
            )

        # --- PHASE 4: VECTOR EMBEDDING GENERATION ---
        chunks = chunk_text(full_extracted_text)
        
        await conn.execute(
            "UPDATE ingestion_tasks SET total_chunks = $2 WHERE task_id = $1;",
            task_id_str, len(chunks)
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
            task_id_str
        )
        logger.info(f"Multi-format visual ingestion task {task_id} successfully closed out.")

    except Exception as e:
        logger.error(f"Multi-format visual worker execution failed on job {task_id}: {str(e)}")
        await conn.execute(
            "UPDATE ingestion_tasks SET status = 'failed', error_message = $2, updated_at = CURRENT_TIMESTAMP WHERE task_id = $1;",
            task_id_str, str(e)
        )
    finally:
        await conn.close()