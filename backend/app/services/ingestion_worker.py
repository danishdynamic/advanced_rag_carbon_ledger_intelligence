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

logger = logging.getLogger("carbon_ledger.ingestion_worker")

# 📊 1. Define the exact shape of data we want Gemini to extract
class CorporateClimateMetrics(BaseModel):
    facility_name: str = Field(description="The primary corporate entity or specific facility/plant name discussed in the document.")
    annual_co2_emissions_tons: float = Field(description="The numeric annual carbon or CO2 emissions in metric tons. Default to 0.0 if not found.")
    regulatory_framework: str = Field(description="The governing framework mentioned (e.g., EU-ETS, CCA, local compliance). Default to 'Baseline'.")

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
    Extracts unstructured data via Gemini Vision, compiles structured financial risk 
    indicators, and populates the vector-search indices concurrently.
    """
    conn = await asyncpg.connect(settings.PRIMARY_DB_URL)
    ai_client = genai.Client()
    
    try:
        await conn.execute(
            "UPDATE ingestion_tasks SET status = 'processing', updated_at = CURRENT_TIMESTAMP WHERE task_id = $1;",
            task_id
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
            
            CRITICAL RULES:
            1. Transcribe all text paragraphs exactly as written.
            2. If you encounter charts, data graphs, or visual diagrams, analyze the pixels and write an exhaustive textual description of the trends, data points, and values shown.
            3. If you encounter tables, extract and format them completely into clean Markdown tables.
            
            Output the raw extracted text and visual summaries directly without introducing meta-commentary.
            """

            response = ai_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[uploaded_file, parsing_prompt]
            )
            
            full_extracted_text = response.text if response.text else ""
            
            # Asynchronous Clean up
            try:
                if uploaded_file.name:
                    ai_client.files.delete(name=uploaded_file.name)
                    logger.info(f"Cleaned up remote staging file: {uploaded_file.name}")
            except Exception as clean_err:
                logger.warning(f"Non-blocking failure cleaning up staged Gemini file: {str(clean_err)}")

        # --- PHASE 3: SAFETY GUARD & ANALYTICS CALCULATION ---
        if not full_extracted_text.strip():
            raise ValueError("Vision extraction pass returned an unparsable or completely empty text payload.")

        # 🎯 NEW: If it's a PDF compliance report, extract structured indicators for the Green Finance engine
        if lower_name.endswith('.pdf'):
            logger.info(f"Executing structured data extraction pass for task {task_id}...")
            
            analysis_prompt = f"""
            Analyze the following extracted document text and extract the specific environmental parameters requested in the output schema.
            
            Document Text:
            {full_extracted_text}
            """
            
            # Force Gemini to return an exact JSON structure matching our Pydantic schema
            structured_response = ai_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=analysis_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=CorporateClimateMetrics,
                ),
            )

            # 🛡️ 1. Extract to a variable and check for None/empty string
            raw_json = structured_response.text
            if not raw_json:
                raise ValueError("Gemini structured extraction returned an empty or missing text payload.")
            
            # 🎯 2. Pylance now knows for a fact that raw_json is strictly a 'str'
            metrics = json.loads(raw_json)
            
            
            facility = metrics.get("facility_name", f"Unknown Facility ({file_name})")
            emissions = float(metrics.get("annual_co2_emissions_tons", 0.0))
            framework = metrics.get("regulatory_framework", "Baseline")
            
            # 🧮 Compute our deterministic business metrics (e.g., carbon pricing baseline at $90/ton)
            carbon_price_baseline = 90.00
            projected_liability = emissions * carbon_price_baseline
            risk_level = "high" if projected_liability > 50000.0 else "low"
            scenario_meta = f"Gemini Parsing Pass - Framework: {framework}"
            
            # Save the analytical result directly to the write database cluster
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