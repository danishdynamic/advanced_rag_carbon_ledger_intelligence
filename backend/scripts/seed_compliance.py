# its acts as ETL ( extract, transform and load ) pipeline

import asyncio
import logging
import asyncpg
from app.config import settings
from app.services.search import compliance_search

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("carbon_ledger.seeder")

# Sample raw regulatory data for testing our pipeline
MOCK_REGULATORY_DATA = [
    {
        "framework_name": "EU CSRD",
        "section_identifier": "Article 19a - Scope 3",
        "text": "Under the Corporate Sustainability Reporting Directive (CSRD), large undertakings must disclose significant indirect greenhouse gas emissions across their entire value chain. This includes Scope 3 emissions such as purchased goods, transport logistics, and end-of-life treatment of sold products. Companies must report these metrics using verifiable calculations aligned with the GHG Protocol."
    },
    {
        "framework_name": "IFRS S2",
        "section_identifier": "Paragraph 29 - Climate Disclosures",
        "text": "IFRS S2 requires entities to provide absolute gross greenhouse gas emissions expressed in metric tonnes of CO2 equivalent (tCO2e), categorized into Scope 1, Scope 2, and Scope 3 emissions. When disclosing Scope 3 emissions, entities must declare the categories included within their boundary definitions and detail the specific emission factors applied."
    },
    {
        "framework_name": "Verra VM0047",
        "section_identifier": "Section 4.1 - Additionality",
        "text": "Afforestation and reforestation projects registered under Verra methodology VM0047 must prove clear financial and regulatory additionality. Carbon credit vintage validation requires satellite canopy density analysis alongside continuous ground-truth biomass measurements over a minimum 20-year permanence commitment loop."
    }
]

async def seed_database():
    logger.info("Connecting to Primary database cluster to seed compliance knowledge base...")
    conn = await asyncpg.connect(settings.PRIMARY_DB_URL)
    
    try:
        for idx, doc in enumerate(MOCK_REGULATORY_DATA):
            logger.info(f"Processing node {idx+1}/{len(MOCK_REGULATORY_DATA)}: {doc['framework_name']} - {doc['section_identifier']}")
            
            # 1. Generate the 1536-dimension embedding via our existing service
            embedding_vector = await compliance_search._generate_embedding(doc["text"])
            vector_str = f"[{','.join(map(str, embedding_vector))}]"
            
            # 2. Insert text, metadata, and vectors simultaneously into Postgres
            # We pass empty JSONB metadata tags {} as a default placeholder
            await conn.execute(
                """
                INSERT INTO compliance_documents (framework_name, section_identifier, raw_text_chunk, metadata_tags, embedding_vector)
                VALUES ($1, $2, $3, $4::jsonb, $5::vector);
                """,
                doc["framework_name"],
                doc["section_identifier"],
                doc["text"],
                "{}",
                vector_str
            )
            
        logger.info("Successfully seeded compliance documentation vector entries!")
    except Exception as e:
        logger.error(f"Seeding execution aborted due to error: {str(e)}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(seed_database())