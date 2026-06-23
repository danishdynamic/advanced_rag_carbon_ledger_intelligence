import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
import asyncpg
import json

from app.database import get_read_db
from app.advanced_rag.query_processor import query_processor
from app.services.search import compliance_search
from app.services.reranker import document_reranker
from google import genai

logger = logging.getLogger("carbon_ledger.routers.compliance")
router = APIRouter(prefix="/api/compliance", tags=["Compliance Intelligence"])
genai_client = genai.Client()

# --- Pydantic API Schemas ---

class ChatTurn(BaseModel):
    role: str = Field(default=..., description="Must be either 'user' or 'assistant'")
    content: str

class ComplianceQueryRequest(BaseModel):
    query: str = Field(default=..., examples=["Compare the disclosure targets for Scope 3 emissions between EU CSRD and IFRS S2."])
    chat_history: list[ChatTurn] = Field(default=[])

class ComplianceQueryResponse(BaseModel):
    answer: str
    is_grounded: bool
    justification_plan: str
    sources: list[dict]

# --- Upgraded Orchestration Loop ---

@router.post("/query", response_model=ComplianceQueryResponse)
async def execute_compliance_rag(
    payload: ComplianceQueryRequest,
    db_conn: asyncpg.Connection = Depends(get_read_db)
):
    """
    Day 1 Advanced RAG Execution Pipeline:
    1. Cognitive Decomposition into structural target JSON sub-plans
    2. Concurrent Hybrid (Vector + Keyword) GIN-indexed cluster lookup
    3. Multi-branch Reciprocal Rank Fusion (RRF) math optimization
    4. Cross-Encoder local Reranking via FlashRank
    5. CRAG Gatekeeper fallback loop to halt hallucinations on poor context matching
    """
    try:
        # Convert history format into basic trace logs
        history_str = "\n".join([f"{t.role}: {t.content}" for t in payload.chat_history])
        
        # 1. Cognitive Structured Intent Decomposition
        query_plan = await query_processor.process_query(payload.query, history_str)
        
        # 2 & 3. Concurrent Multi-Query Execution & Reciprocal Rank Fusion
        fused_candidates = await compliance_search.hybrid_decomposed_search(
            execution_steps=query_plan.execution_steps, 
            conn=db_conn
        )
        
        if not fused_candidates:
            return ComplianceQueryResponse(
                answer="No validated compliance documentation fragments match your requested search items.",
                is_grounded=False,
                justification_plan=query_plan.analysis_justification,
                sources=[]
            )

        # Map current schema fields cleanly into dictionary nodes expected by FlashRank
        normalized_candidates = [
            {
                "id": c["id"],
                "text": c["raw_text_chunk"],
                "meta": {
                    "framework_name": c["framework_name"],
                    "section_identifier": c["section_identifier"],
                    "metadata_tags": json.loads(c["metadata_tags"]) if isinstance(c["metadata_tags"], str) else c["metadata_tags"]
                }
            } for c in fused_candidates
        ]

        # 4. High-Speed Local Reranking
        # We flatten out the complex branches down to the top 4 definitive texts
        reranked_results = document_reranker.rerank(payload.query, normalized_candidates, top_n=4)
        
        # 5. Corrective RAG (CRAG) Gatekeeper Threshold Check
        # FlashRank outputs an explicit 'score' between 0.0 and 1.0 per block
        MAX_TRUST_THRESHOLD = 0.25 
        top_score = reranked_results[0].get("score", 0.0) if reranked_results else 0.0
        
        logger.info(f"Top cross-encoder reranked candidate confidence metric: {top_score}")
        
        if top_score < MAX_TRUST_THRESHOLD:
            logger.warning(f"CRAG Circuit triggered. Confidence {top_score} falls below baseline safety threshold.")
            return ComplianceQueryResponse(
                answer="Verification Error: The system located related compliance information, but the data density fell short of safety validation rules. Aborting generation loop to prevent structural reporting hallucinations.",
                is_grounded=False,
                justification_plan=f"{query_plan.analysis_justification} -> [CRAG Circuit Triggered: Top score {top_score:.4f} < {MAX_TRUST_THRESHOLD}]",
                sources=[
                    {
                        "id": r.get("id"),
                        "framework_name": r.get("meta", {}).get("framework_name"),
                        "section_identifier": r.get("meta", {}).get("section_identifier")
                    } for r in reranked_results[:2]
                ]
            )

        # Synthesize Context for Validated Pass
        context_str = ""
        sources_meta = []
        for idx, item in enumerate(reranked_results):
            meta = item.get("meta", {})
            context_str += f"--- NODE {idx+1} ({meta.get('framework_name')} - {meta.get('section_identifier')}) ---\n"
            context_str += f"{item.get('text')}\n\n"
            sources_meta.append({
                "id": item.get("id"),
                "framework_name": meta.get("framework_name"),
                "section_identifier": meta.get("section_identifier")
            })

        generation_prompt = f"""
        You are a principal carbon risk auditor. Answer the user prompt leveraging ONLY the authorized context below.
        
        AUTHORIZED DOCUMENTS:
        {context_str}
        
        TARGET QUESTION:
        {payload.query}
        
        Provide an exhaustive, objective response citing section numbers naturally.
        """

        response = genai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=generation_prompt
        )

        return ComplianceQueryResponse(
            answer=response.text.strip() if response.text else "Failed to finalize audit synthesis text.",
            is_grounded=True,
            justification_plan=query_plan.analysis_justification,
            sources=sources_meta
        )

    except Exception as e:
        logger.error(f"Failed pipeline orchestration pass: {str(e)}")
        raise HTTPException(status_code=500, detail="Advanced RAG compilation pipeline processing failure.")