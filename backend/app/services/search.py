import logging
from google import genai
from google.genai import types
import asyncpg
from app.config import settings

logger = logging.getLogger("carbon_ledger.search")

class ComplianceSearchService:
    def __init__(self):
        # Instantiate the official client mapping to your Gemini API key
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        # Using Google's native multimodal/text embedding framework
        self.embedding_model = "gemini-embedding-2"

    async def _generate_embedding(self, text: str) -> list[float]:
        """Generates a high-fidelity 1536-dimensional vector array for semantic search."""
        try:
            response = self.client.models.embed_content(
                model=self.embedding_model,
                contents=text,
                config=types.EmbedContentConfig(
                    output_dimensionality=1536  # Matches our database column configuration exactly
                )
            )
            
            # --- PYLANCE TYPE GUARDS ---
            if response.embeddings is None or len(response.embeddings) == 0:
                raise RuntimeError("Gemini API returned an empty embedding response sequence.")
                
            values = response.embeddings[0].values
            if values is None:
                raise RuntimeError("Gemini embedding vector coordinates are completely null.")
            # ---------------------------
            
            return values
        except Exception as e:
            logger.error(f"Gemini embedding API call failed: {str(e)}")
            raise RuntimeError("Failed to compute text embeddings.")

    async def semantic_search(self, query_text: str, conn: asyncpg.Connection, limit: int = 25) -> list[dict]:
        """
        Executes a high-speed cosine distance vector search against the compliance index.
        Utilizes pgvector '<=>' operator (Cosine Distance).
        """
        # 1. Transform raw text into mathematical vectors
        vector_query = await self._generate_embedding(query_text)
        
        # Convert python list into a string format that pgvector cleanly interprets
        vector_str = f"[{','.join(map(str, vector_query))}]"

        # 2. Run the read query against the database
        # Cosine Similarity = 1 - Cosine Distance
        sql = """
            SELECT 
                id, 
                framework_name, 
                section_identifier, 
                raw_text_chunk, 
                metadata_tags,
                (1 - (embedding_vector <=> $1::vector)) AS similarity_score
            FROM compliance_documents
            WHERE (1 - (embedding_vector <=> $1::vector)) > 0.35
            ORDER BY embedding_vector <=> $1::vector ASC
            LIMIT $2;
        """
        
        try:
            records = await conn.fetch(sql, vector_str, limit)
            
            # Map database records cleanly back to standard dictionary types
            results = [
                {
                    "id": record["id"],
                    "framework_name": record["framework_name"],
                    "section_identifier": record["section_identifier"],
                    "raw_text_chunk": record["raw_text_chunk"],
                    "metadata_tags": record["metadata_tags"],
                    "score": float(record["similarity_score"])
                }
                for record in records
            ]
            logger.info(f"Retrieved {len(results)} raw matching context blocks from Postgres.")
            return results
        except Exception as e:
            logger.error(f"Database vector lookup failed: {str(e)}")
            return []

# Singleton instance
compliance_search = ComplianceSearchService()