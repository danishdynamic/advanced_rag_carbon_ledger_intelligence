import logging
from google import genai
from google.genai import types
from app.config import settings

logger = logging.getLogger("carbon_ledger.rewriter")

class QueryRewriter:
    def __init__(self):
        # Initialize the official Google GenAI Client
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model_name = "gemini-2.5-flash"

    async def rewrite_query(self, current_query: str, chat_history: list[dict]) -> str:
        """
        Analyzes conversation logs and transforms shorthand follow-ups 
        into a fully articulated compliance search query.
        """
        if not chat_history:
            return current_query

        # Format historical records for the prompt context
        history_context = ""
        for turn in chat_history:
            role = "User" if turn.get("role") == "user" else "Assistant"
            history_context += f"{role}: {turn.get('content')}\n"

        prompt = f"""
        You are an enterprise green finance data engineer. Your task is to analyze the following conversation history and the latest user query, then produce a optimized, standalone search query suitable for a vector and full-text database lookup regarding carbon compliance, emissions tracking, or ESG frameworks.

        CONVERSATION HISTORY:
        {history_context}

        LATEST USER QUERY:
        {current_query}

        INSTRUCTIONS:
        - If the latest query stands completely on its own, return it exactly as written.
        - If the latest query references pronouns ("it", "they", "those rules") or relies on historical context, reformulate it into a dense, explicit search terms phrase incorporating proper nouns from the history (e.g., "EU CSRD Scope 3 logistics requirements").
        - Output ONLY the final raw search string. Do not add introductions, explanations, quotes, or markdown.
        """

        try:
            # Execute standard content generation
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0, # Complete deterministic precision for structural search queries
                )
            )
            
            rewritten = response.text.strip() if response.text else current_query
            logger.info(f"Query reformulated: '{current_query}' -> '{rewritten}'")
            return rewritten

        except Exception as e:
            logger.error(f"Failed to reformulate query context: {str(e)}")
            # Fall back to the user's raw query to keep the system operational if API drops out
            return current_query

# Singleton instance
query_rewriter = QueryRewriter()