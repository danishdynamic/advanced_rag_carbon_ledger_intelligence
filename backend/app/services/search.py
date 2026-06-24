import logging
import asyncio
import json
import asyncpg
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from app.config import settings

logger = logging.getLogger("carbon_ledger.search")

# --- Pydantic Blueprints for CRAG & Decomposition ---

class EvaluationSchema(BaseModel):
    is_relevant: bool = Field(description="True if the retrieved text context chunks contain useful data to answer the main query. False otherwise.")
    confidence_score: float = Field(description="Confidence rating between 0.0 and 1.0.")

class SubQueryBlueprint(BaseModel):
    sub_query: str = Field(description="The decomposed atomic sub-query targeted for search extraction.")
    framework_filter: str | None = Field(default=None, description="Target compliance framework or Null.")

class QueryDecompositionSchema(BaseModel):
    sub_queries: list[SubQueryBlueprint] = Field(description="List of 1 to 3 distinct sub-queries required to fully evaluate the main question.")


class AdvancedComplianceSearch:
    def __init__(self):
        self.client = genai.Client()
        self.embedding_model = "gemini-embedding-001"

    async def _generate_embedding(self, text: str) -> list[float]:
        """Generates a standard 3072-dimension vector via Gemini API (gemini-embedding-001 default)."""
        try:
            response = await self.client.aio.models.embed_content(
                model=self.embedding_model,
                contents=text
            )
            if not response.embeddings or response.embeddings[0].values is None:
                raise ValueError("Gemini API returned an empty or uninitialized embedding payload.")
            return [float(x) for x in response.embeddings[0].values]
        except Exception as e:
            logger.error(f"Failed to generate vector embedding: {str(e)}")
            raise e

    async def _vector_search_worker(self, query: str, framework: str | None, pool: asyncpg.Pool, limit: int) -> list[dict]:
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
        async with pool.acquire() as conn: 
            rows = await conn.fetch(sql, framework, vector_str, limit)
            return [dict(row) for row in rows]

    async def _keyword_search_worker(self, query: str, framework: str | None, pool: asyncpg.Pool, limit: int) -> list[dict]:
        """Performs PostgreSQL full-text keyword matching using plainto_tsquery."""
        sql = """
            SELECT id, framework_name, section_identifier, raw_text_chunk, metadata_tags
            FROM compliance_documents
            WHERE ($1::text IS NULL OR framework_name = $1)
              AND to_tsvector('english', raw_text_chunk) @@ plainto_tsquery('english', $2)
            LIMIT $3;
        """
        async with pool.acquire() as conn:
            rows = await conn.fetch(sql, framework, query, limit)
            return [dict(row) for row in rows]

    def compute_rrf(self, vector_groups: list[list[dict]], keyword_groups: list[list[dict]], k: int = 60) -> list[dict]:
        """Fuses multi-query parallel vector and keyword results using Reciprocal Rank Fusion."""
        rrf_scores = {}
        doc_registry = {}

        def process_ranking_list(results_list):
            for rank, doc in enumerate(results_list, start=1):
                doc_id = doc["id"]
                if doc_id not in doc_registry:
                    doc_registry[doc_id] = doc
                rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (k + rank))

        for execution_stream in vector_groups + keyword_groups:
            process_ranking_list(execution_stream)

        sorted_ids = sorted(rrf_scores.items(), key=lambda item: item[1], reverse=True)
        
        final_docs = []
        for doc_id, score in sorted_ids:
            hydrated_doc = doc_registry[doc_id]
            hydrated_doc["rrf_score"] = score
            final_docs.append(hydrated_doc)
            
        return final_docs

    async def hybrid_decomposed_search(self, execution_steps: list, pool: asyncpg.Pool, limit_per_worker: int = 15) -> list[dict]:
        """Orchestrates parallel multi-query execution threads concurrently over connection."""
        vector_tasks = []
        keyword_tasks = []

        for step in execution_steps:
            vector_tasks.append(self._vector_search_worker(step.sub_query, step.framework_filter, pool, limit_per_worker))
            keyword_tasks.append(self._keyword_search_worker(step.sub_query, step.framework_filter, pool, limit_per_worker))

        vector_results_groups = await asyncio.gather(*vector_tasks)
        keyword_results_groups = await asyncio.gather(*keyword_tasks)

        return self.compute_rrf(vector_results_groups, keyword_results_groups)

    # 🚀 NEW: Deep Cognitive Trace Entrypoint for the Chat Interface
    async def retrieve_cognitive_trace(self, query: str, pool: asyncpg.Pool) -> dict:
        logger.info(f"Decomposing core user prompt into sub-queries: '{query}'")
        
        # 1. Dynamically split query using Structured Outputs
        decomp_prompt = f"Analyze this user question and break it into structural sub-queries for parallel database indexing lookup: {query}"
        
        try:
            decomp_response = await self.client.aio.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=decomp_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=QueryDecompositionSchema
                )
            )
            
            raw_decomp_text = decomp_response.text or "{}"
            decomp_data = json.loads(raw_decomp_text)
            # Reconstruct into blueprint objects for compatibility
            execution_steps = [SubQueryBlueprint(**step) for step in decomp_data.get("sub_queries", [])]
        except Exception as e:
            logger.warning(f"Query decomposition failed, falling back to raw query syntax: {str(e)}")
            execution_steps = [SubQueryBlueprint(sub_query=query, framework_filter=None)]

        # Extract literal string lists for the tracing panel display
        trace_sub_queries = [step.sub_query for step in execution_steps]

        # 2. Run your existing heavy hybrid RRF engine
        fused_results = await self.hybrid_decomposed_search(execution_steps, pool, limit_per_worker=5)
        top_slices = fused_results[:3] # Target top 3 unified contexts

        source_references = []
        retrieved_texts = []
        
        for r in top_slices:
            ref = {
                "file_name": r["framework_name"],
                "section": r["section_identifier"],
                "text_snippet": r["raw_text_chunk"],
                "similarity": round(r.get("rrf_score", 0.0) * 100, 1) # Display RRF metric as visibility percentage
            }
            source_references.append(ref)
            retrieved_texts.append(r["raw_text_chunk"])

        combined_context = "\n\n".join(retrieved_texts)

        if not source_references:
            return {
                "sub_queries": trace_sub_queries,
                "evaluation_status": "IRRELEVANT",
                "source_references": [],
                "context": "",
                "confidence_score": 0.0
            }

        # 3. Corrective RAG Evaluation
        eval_prompt = f"Evaluate whether this context contains hard objective metrics to answer the user query.\nQuery: {query}\nContext: {combined_context}"
        try:
            eval_response = await self.client.aio.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=eval_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=EvaluationSchema
                )
            )
            
            raw_eval_text = eval_response.text or "{}"
            eval_data = json.loads(raw_eval_text)

            status = "CORRECT" if eval_data.get("is_relevant") else "AMBIGUOUS"
            confidence = eval_data.get("confidence_score", 0.5)
        except Exception:
            status = "AMBIGUOUS"
            confidence = 0.5

        return {
            "sub_queries": trace_sub_queries,
            "evaluation_status": status,
            "source_references": source_references,
            "context": combined_context,
            "confidence_score": confidence
        }

compliance_search = AdvancedComplianceSearch()