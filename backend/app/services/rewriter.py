import logging
import asyncpg
from google import genai
from google.genai import types
from app.config import settings
from .quota_manager import check_and_increment_quota  

logger = logging.getLogger("carbon_ledger.rewriter")

class QueryRewriter:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        # ⚡ Updated to the Lite tier model
        self.model_name = "gemini-3.1-flash-lite"

    async def rewrite_query(self, current_query: str, chat_history: list[dict], db_conn: asyncpg.Connection) -> str:
        """
        Analyzes conversation logs and transforms shorthand follow-ups 
        into a fully articulated compliance search query.
        """
        if not chat_history:
            return current_query

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
            # 🛡️ Quota Check: Executed right before calling the model
            await check_and_increment_quota(db_conn)
            
            # ⚡ Optimized: Switched from sync .generate_content to non-blocking async (.aio)
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,  # Complete deterministic precision for structural search queries
                )
            )
            
            rewritten = response.text.strip() if response.text else current_query
            logger.info(f"Query reformulated: '{current_query}' -> '{rewritten}'")
            return rewritten

        except Exception as e:
            logger.error(f"Failed to reformulate query context: {str(e)}")
            return current_query

# Singleton instance
query_rewriter = QueryRewriter()