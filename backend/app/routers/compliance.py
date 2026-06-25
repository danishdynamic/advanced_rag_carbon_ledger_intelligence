import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
import asyncpg
import json

from app.database import get_read_db
from app.advanced_rag.query_processor import query_processor
from app.services.search import compliance_search
from app.services.reranker import document_reranker
from app.services.evaluator import RagasEvaluationService, RagasScores  # 🎯 New Import
from google import genai

logger = logging.getLogger("carbon_ledger.routers.compliance")
router = APIRouter(prefix="/api/compliance", tags=["Compliance Intelligence"])
genai_client = genai.Client()


class ChatTurn(BaseModel):
    role: str = Field(default=..., description="Must be either 'user' or 'assistant'")
    content: str


class ComplianceQueryRequest(BaseModel):
    query: str
    chat_history: list[ChatTurn] = Field(default=[])


class ComplianceQueryResponse(BaseModel):
    answer: str
    is_grounded: bool
    justification_plan: str
    sources: list[dict]
    evaluation: RagasScores  # 🎯 New Field: Inline telemetry feedback metrics


@router.post("/query", response_model=ComplianceQueryResponse)
async def execute_compliance_rag(
    payload: ComplianceQueryRequest, db_pool: asyncpg.Pool = Depends(get_read_db)
):
    try:
        history_str = "\n".join(
            [f"{t.role}: {t.content}" for t in payload.chat_history]
        )
        query_plan = await query_processor.process_query(payload.query, history_str)

        fused_candidates = await compliance_search.hybrid_decomposed_search(
            execution_steps=query_plan.execution_steps, pool=db_pool
        )

        if not fused_candidates:
            return ComplianceQueryResponse(
                answer="No validated compliance documentation fragments match your requested search items.",
                is_grounded=False,
                justification_plan=query_plan.analysis_justification,
                sources=[],
                evaluation=RagasScores(
                    faithfulness_score=0.0,
                    relevance_score=0.0,
                    justification="No context retrieved.",
                ),
            )

        normalized_candidates = [
            {
                "id": c["id"],
                "text": c["raw_text_chunk"],
                "meta": {
                    "framework_name": c["framework_name"],
                    "section_identifier": c["section_identifier"],
                    "metadata_tags": json.loads(c["metadata_tags"])
                    if isinstance(c["metadata_tags"], str)
                    else c["metadata_tags"],
                },
            }
            for c in fused_candidates
        ]

        reranked_results = document_reranker.rerank(
            payload.query, normalized_candidates, top_n=4
        )
        MAX_TRUST_THRESHOLD = 0.25
        top_score = reranked_results[0].get("score", 0.0) if reranked_results else 0.0

        if top_score < MAX_TRUST_THRESHOLD:
            return ComplianceQueryResponse(
                answer="Verification Error: Data density fell short of safety validation rules.",
                is_grounded=False,
                justification_plan=f"{query_plan.analysis_justification} -> [CRAG Circuit Triggered]",
                sources=[],
                evaluation=RagasScores(
                    faithfulness_score=0.0,
                    relevance_score=0.1,
                    justification="CRAG gatekeeper execution halt.",
                ),
            )

        context_str = ""
        sources_meta = []
        for idx, item in enumerate(reranked_results):
            meta = item.get("meta", {})
            context_str += f"--- NODE {idx + 1} ({meta.get('framework_name')} - {meta.get('section_identifier')}) ---\n"
            context_str += f"{item.get('text')}\n\n"
            sources_meta.append(
                {
                    "id": item.get("id"),
                    "framework_name": meta.get("framework_name"),
                    "section_identifier": meta.get("section_identifier"),
                }
            )

        generation_prompt = f"""
        You are a principal carbon risk auditor. Answer the user prompt leveraging ONLY the authorized context below.
        AUTHORIZED DOCUMENTS:
        {context_str}
        TARGET QUESTION:
        {payload.query}
        """

        response = genai_client.models.generate_content(
            model="gemini-3.1-flash-lite", contents=generation_prompt
        )
        generated_text = response.text.strip() if response.text else ""

        # 🎯 2. RUN RAGAS EVALUATION ASYNC ON SYNTHESIZED OUTPUT
        eval_metrics = await RagasEvaluationService.evaluate_generation(
            query=payload.query,
            retrieved_context=context_str,
            generated_answer=generated_text,
        )

        return ComplianceQueryResponse(
            answer=generated_text,
            is_grounded=eval_metrics.faithfulness_score > 0.7,
            justification_plan=query_plan.analysis_justification,
            sources=sources_meta,
            evaluation=eval_metrics,  # 🚀 Real-time feedback object populated!
        )

    except Exception as e:
        logger.error(f"Failed pipeline orchestration pass: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Advanced RAG compilation pipeline processing failure.",
        )
