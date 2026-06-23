import logging
import asyncio
import json
import asyncpg
from google import genai
from app.config import settings

logger = logging.getLogger("carbon_ledger.search")

class AdvancedComplianceSearch:
    def __init__(self):
        self.client = genai.Client()
        self.embedding_model = "text-embedding-004"

    async def _generate_embedding(self, text: str) -> list[float]:
        """Generates a standard 1536-dimension vector via Gemini API."""
        try:
            response = self.client.models.embed_content(
                model=self.embedding_model,
                contents=text
            )
            
            # 1. Defensive verification guard clauses
            if not response.embeddings or response.embeddings[0].values is None:
                raise ValueError("Gemini API returned an empty or uninitialized embedding payload.")
            
            # 2. Force an explicit list comprehension cast to guarantee a pure list[float] return type
            return [float(x) for x in response.embeddings[0].values]
            
        except Exception as e:
            logger.error(f"Failed to generate vector embedding: {str(e)}")
            raise e

    async def _vector_search_worker(self, query: str, framework: str | None, conn: asyncpg.Connection, limit: int) -> list[dict]:
        """Performs pgvector cosine distance matching over leased replica connections."""
        vector = await self._generate_embedding(query)
        vector_str = f"[{','.join(map(str, vector))}]"
        
        sql = """
            SELECT id, framework_name, section_identifier, raw_text_chunk, metadata_tags
            FROM compliance_documents
            WHERE ($1::text IS NULL OR framework_name = $1)
            ORDER BY embedding_vector <=> $2::vector
            LIMIT $3;
        """
        rows = await conn.fetch(sql, framework, vector_str, limit)
        return [dict(row) for row in rows]

    async def _keyword_search_worker(self, query: str, framework: str | None, conn: asyncpg.Connection, limit: int) -> list[dict]:
        """Performs PostgreSQL full-text keyword matching using plainto_tsquery."""
        sql = """
            SELECT id, framework_name, section_identifier, raw_text_chunk, metadata_tags
            FROM compliance_documents
            WHERE ($1::text IS NULL OR framework_name = $1)
              AND to_tsvector('english', raw_text_chunk) @@ plainto_tsquery('english', $2)
            LIMIT $3;
        """
        rows = await conn.fetch(sql, framework, query, limit)
        return [dict(row) for row in rows]

    def compute_rrf(self, vector_groups: list[list[dict]], keyword_groups: list[list[dict]], k: int = 60) -> list[dict]:
        """
        Fuses multi-query parallel vector and keyword results using Reciprocal Rank Fusion.
        Deduplicates overlapping entries across different execution branches.
        """
        rrf_scores = {}
        doc_registry = {}

        def process_ranking_list(results_list):
            for rank, doc in enumerate(results_list, start=1):
                doc_id = doc["id"]
                if doc_id not in doc_registry:
                    doc_registry[doc_id] = doc
                # Apply reciprocal rank score formula
                rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (k + rank))

        # Score every parallel search stream execution list
        for execution_stream in vector_groups + keyword_groups:
            process_ranking_list(execution_stream)

        # Sort documents by their collective fused RRF scores descending
        sorted_ids = sorted(rrf_scores.items(), key=lambda item: item[1], reverse=True)
        
        final_docs = []
        for doc_id, score in sorted_ids:
            hydrated_doc = doc_registry[doc_id]
            # Inject RRF score into payload for tracking transparency
            hydrated_doc["rrf_score"] = score
            final_docs.append(hydrated_doc)
            
        return final_docs

    async def hybrid_decomposed_search(self, execution_steps: list, conn: asyncpg.Connection, limit_per_worker: int = 15) -> list[dict]:
        """
        Orchestrates parallel multi-query execution threads concurrently over a single shared connection lifecycle.
        """
        vector_tasks = []
        keyword_tasks = []

        for step in execution_steps:
            # step.sub_query and step.framework_filter map directly to our parsed Pydantic blueprint
            vector_tasks.append(self._vector_search_worker(step.sub_query, step.framework_filter, conn, limit_per_worker))
            keyword_tasks.append(self._keyword_search_worker(step.sub_query, step.framework_filter, conn, limit_per_worker))

        # Fire ALL search streams simultaneously across the database connection pool mapping
        vector_results_groups = await asyncio.gather(*vector_tasks)
        keyword_results_groups = await asyncio.gather(*keyword_tasks)

        # Fuse disparate branches into an optimized unified dataset
        return self.compute_rrf(vector_results_groups, keyword_results_groups)

# Instantiate singleton service mapping
compliance_search = AdvancedComplianceSearch()