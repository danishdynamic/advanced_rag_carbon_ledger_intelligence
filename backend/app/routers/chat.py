import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import asyncpg
from google import genai
from google.genai import types
from app.database import get_read_db, db_manager
from app.services.search import compliance_search

logger = logging.getLogger("carbon_ledger.routers.chat")
router = APIRouter(prefix="/api/chat", tags=["Compliance Cognitive Chat"])

class ChatRequest(BaseModel):
    prompt: str

class ChatResponse(BaseModel):
    answer: str
    sub_queries: list[str]
    evaluation_status: str  # CORRECT, AMBIGUOUS, IRRELEVANT
    confidence_score: float
    source_references: list[dict]

@router.post("/query", response_model=ChatResponse)
async def process_compliance_chat(
    payload: ChatRequest):
    try:
        # 1. Gather our cognitive trace definitions
        pool = db_manager.read_pool

        if pool is None:
            logger.error("Database connection pool is uninitialized.")
            raise HTTPException(
                status_code=503, 
                detail="Database cluster pool is offline or restarting."
            )
        
        trace = await compliance_search.retrieve_cognitive_trace(payload.prompt, pool)
        
        # 2. Construct final response message using the context
        ai_client = genai.Client()
        
        system_instruction = """
        You are the CarbonLedger Compliance Intelligence engine. Answer the user's questions truthfully using only the provided context. 
        If the context is insufficient or ambiguous, politely inform the user of what is missing.
        """
        
        prompt_context = f"""
        Context:
        {trace['context']}
        
        User Query: {payload.prompt}
        """
        
        response = await ai_client.aio.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=prompt_context,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2
            )
        )
        
        return ChatResponse(
            answer=response.text if response.text else "Unable to generate structural answer synthesis.",
            sub_queries=trace["sub_queries"],
            evaluation_status=trace["evaluation_status"],
            confidence_score=trace["confidence_score"],
            source_references=trace["source_references"]
        )
        
    except Exception as e:
        logger.error(f"Cognitive chat transaction failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal chat generation loop crashed.")