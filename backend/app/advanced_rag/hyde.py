import logging
from google import genai
from app.config import settings

logger = logging.getLogger(__name__)

class HyDEGenerator:
    """
    Implements Hypothetical Document Embeddings (HyDE).
    Transforms dense user questions into compliance-style declarative paragraphs 
    to maximize vector similarity accuracy against corporate sustainability logs.
    """
    def __init__(self):
        # Initializes using GEMINI_API_KEY from environment variables automatically
        self.client = genai.Client()
        self.model_name = "gemini-2.5-flash"

    async def generate_hypothetical_doc(self, query: str) -> str:
        """
        Generates a synthetic textbook/compliance response to use as a vector anchor.
        """
        prompt = f"""
        You are a senior lead compliance auditor specializing in GHG Protocol corporate accounting, CSRD, and ESG disclosures.
        
        Write a precise, highly technical paragraph that serves as a direct answer or ideal documentation excerpt for the query below.
        
        Guidelines:
        - Use standard professional jargon (e.g., Scope 1 fugitives, emission factors, activity metrics, boundary definitions).
        - Do NOT include introductory phrases like "Sure, here is an example..." or "Based on your request...".
        - Provide ONLY the direct, cold, factual compliance-style text itself.
        
        User Query: {query}
        
        Hypothetical Document Segment:
        """
        
        try:
            # We run this synchronously inside the thread pool or cleanly await via SDK
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            
            hypothetical_doc = response.text.strip()
            logger.info("Successfully synthesized HyDE document vector anchor.")
            return hypothetical_doc
            
        except Exception as e:
            logger.error(f"HyDE synthesis failed: {str(e)}. Falling back to raw query.")
            return query