import logging
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

logger = logging.getLogger("carbon_ledger.services.evaluator")
genai_client = genai.Client()


class RagasScores(BaseModel):
    faithfulness_score: float = Field(
        ...,
        description="Score from 0.0 to 1.0 indicating if claims are explicitly supported by context.",
    )
    relevance_score: float = Field(
        ...,
        description="Score from 0.0 to 1.0 indicating if the answer directly addresses the initial user query.",
    )
    justification: str = Field(
        ..., description="Brief logical explanation of the assigned scores."
    )


class RagasEvaluationService:
    @classmethod
    async def evaluate_generation(
        cls, query: str, retrieved_context: str, generated_answer: str
    ) -> RagasScores:
        """
        Asynchronously runs a G-Eval style assessment loop on the RAG payload
        to mathematically score synthesis accuracy and eliminate hallucination drift.
        """
        eval_prompt = f"""
        You are an expert AI system validator evaluating a Retrieval-Augmented Generation pipeline.
        Analyze the relationship between the target user query, the context retrieved, and the generated answer.
        
        CRITERIA:
        1. Faithfulness: Is every single factual point in the generated answer strictly derived from the retrieved context? Deduct heavily for any outside knowledge or unverified assertions.
        2. Answer Relevance: Does the generated answer directly address the target user query without unnecessary fluff?
        
        INPUT DATA:
        - TARGET USER QUERY: {query}
        - RETRIEVED CONTEXT NODES: {retrieved_context}
        - GENERATED ANSWER: {generated_answer}
        """

        try:
            # Enforce strict structured Pydantic output from Gemini for deterministic tracking
            response = genai_client.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=eval_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=RagasScores,
                    temperature=0.0,  # Force deterministic evaluation math
                ),
            )

            raw_json = response.text if response.text else "{}"

            return RagasScores.model_validate_json(raw_json)
        except Exception as e:
            logger.error(f"RAGAS evaluation engine failure: {str(e)}")
            return RagasScores(
                faithfulness_score=0.0,
                relevance_score=0.0,
                justification=f"Evaluation failed due to engine runtime exception: {str(e)}",
            )
