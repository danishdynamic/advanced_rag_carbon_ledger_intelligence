import logging
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("carbon_ledger.query_processor")

# --- Structured Output Schema Definitions ---

class SubQueryElement(BaseModel):
    sub_query: str = Field(
        ..., 
        description="A distinct, standalone search phrase targeted at keyword or vector retrieval."
    )
    framework_filter: str | None = Field(
        default=None, 
        description="Targeted regulatory framework if explicitly isolated (e.g., 'EU CSRD', 'IFRS S2', 'Verra'). Otherwise null."
    )

class DecomposedQueryPlan(BaseModel):
    analysis_justification: str = Field(..., description="Brief explanation of why the query was broken down or kept whole.")
    execution_steps: list[SubQueryElement] = Field(..., description="List of sub-queries to run concurrently.")

# --- Processor Service ---

class CognitiveQueryProcessor:
    def __init__(self):
        self.client = genai.Client()
        self.model_name = "gemini-2.5-flash"

    async def process_query(self, user_query: str, history_context: str = "") -> DecomposedQueryPlan:
        """
        Decomposes complex, comparative queries into separate target lookups
        and isolates metadata filtering parameters using native structured JSON schema constraints.
        """
        prompt = f"""
        You are a principal compliance systems architect. Analyze the incoming user query (and historical context if present), determine if it requires cross-referencing multiple separate compliance topics, and split it into clean, isolated search terms.

        CONVERSATION HISTORY CONTEXT:
        {history_context}

        INCOMING USER QUERY:
        {user_query}

        INSTRUCTIONS:
        1. If the query asks to compare two things (e.g., 'Compare CSRD and IFRS S2 logistics rules'), split it into two separate execution steps—one for each framework.
        2. Extract any specific framework filter naming constraints into the framework_filter property.
        3. Keep phrases clean, dense, and optimized for vector distance calculations.
        """

        try:
            # Enforce structured output via the native Google GenAI configuration parameters
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=DecomposedQueryPlan,
                    temperature=0.1
                )
            )

            # The SDK automatically handles verification and validates against your Pydantic schema
            if not response.text:
                raise RuntimeError("Empty response received from cognitive parsing engine.")
                
            validated_plan = DecomposedQueryPlan.model_validate_json(response.text)
            logger.info(f"Query decomposed successfully into {len(validated_plan.execution_steps)} steps.")
            return validated_plan

        except Exception as e:
            logger.error(f"Failed cognitive query decomposition execution: {str(e)}")
            # Fail-safe default: Wrap the original query intact so the retrieval loop doesn't break
            return DecomposedQueryPlan(
                analysis_justification="Fallback to default baseline processing on error.",
                execution_steps=[SubQueryElement(sub_query=user_query, framework_filter=None)]
            )

# Singleton instance
query_processor = CognitiveQueryProcessor()