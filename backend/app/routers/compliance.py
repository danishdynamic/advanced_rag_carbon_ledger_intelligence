import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
import asyncpg

from app.database import get_read_db
from app.services.rewriter import query_rewriter
from app.services.search import compliance_search
from app.services.reranker import document_reranker
from google import genai

logger = logging.getLogger("carbon_ledger.routers.compliance")

router = APIRouter(prefix="/api/compliance", tags=["Compliance Intelligence"])

# Initialize a standard Gemini client inside the router for the final response generation
genai_client = genai.Client()

# --- Request / Response Pydantic Schemas ---

class ChatTurn(BaseModel):
    role: str = Field(..., description="Must be either 'user' or 'assistant'")
    content: str

class ComplianceQueryRequest(BaseModel):
    query: str = Field(
        default=..., 
        examples=["What are the disclosure rules for Scope 3 emissions?"]
    )
    chat_history: list[ChatTurn] = Field(default=[])

class ComplianceQueryResponse(BaseModel):
    answer: str
    rewritten_query: str
    sources: list[dict]

# --- Orchestrated Endpoint ---

@router.post("/query", response_model=ComplianceQueryResponse)
async def execute_compliance_rag(
    payload: ComplianceQueryRequest,
    db_conn: asyncpg.Connection = Depends(get_read_db)
):
    """
    Orchestrates the entire RAG lifecycle:
    1. Rewrites intent based on history context
    2. Performs pgvector semantic vector search against read replicas
    3. Trims candidate results via local FlashRank Cross-Encoder
    4. Generates a strictly grounded compliance answer via Gemini 2.5 Flash
    """
    try:
        # Convert Pydantic chat history models back to raw dictionaries for our rewriter service
        history_dicts = [turn.model_dump() for turn in payload.chat_history]
        
        # 1. Contextual Query Rewriting
        optimized_query = await query_rewriter.rewrite_query(payload.query, history_dicts)
        
        # 2. Vector Database Semantic Retrieval (Leased from Read Replica Pool)
        raw_candidates = await compliance_search.semantic_search(optimized_query, db_conn, limit=20)
        
        if not raw_candidates:
            return ComplianceQueryResponse(
                answer="I couldn't locate any matching compliance documentation in the registry database to answer your request accurately.",
                rewritten_query=optimized_query,
                sources=[]
            )
            
        # 3. Local High-Speed Cross-Encoder Reranking
        reranked_results = document_reranker.rerank(optimized_query, raw_candidates, top_n=4)
        
        # 4. Synthesizing Context and Grounding Prompt for Gemini
        context_str = ""
        sources_meta = []
        
        for idx, item in enumerate(reranked_results):
            meta = item.get("meta", {})
            context_str += f"--- DOCUMENT NODE {idx+1} ({meta.get('framework_name')} - {meta.get('section_identifier')}) ---\n"
            context_str += f"{item.get('text')}\n\n"
            
            sources_meta.append({
                "id": item.get("id"),
                "framework_name": meta.get("framework_name"),
                "section_identifier": meta.get("section_identifier")
            })

        generation_prompt = f"""
        You are an expert carbon compliance assistant specializing in regulatory frameworks (like EU CSRD, IFRS S2, and Verra methodologies). 
        Answer the user's question using ONLY the verified regulatory text snippets provided below.

        VERIFIED REGULATORY BACKGROUND:
        {context_str}

        USER QUESTION:
        {optimized_query}

        STRICT INSTRUCTIONS:
        - Base your answer entirely on the provided document snippets.
        - If the provided text does not contain sufficient facts to answer the question, state cleanly that you cannot find sufficient cross-references. Do not speculate.
        - Cite the framework name and section identifier naturally in your response when referring to data.
        """

        # Generate the final authoritative answer
        response = genai_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=generation_prompt
        )
        
        return ComplianceQueryResponse(
            answer=response.text.strip() if response.text else "Generation cycle failed to yield clear insights.",
            rewritten_query=optimized_query,
            sources=sources_meta
        )

    except Exception as e:
        logger.error(f"Critical error throughout compliance RAG execution pipeline: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal processing error within compliance execution chain.")