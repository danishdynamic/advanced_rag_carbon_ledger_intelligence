import logging
from flashrank import Ranker, RerankRequest

logger = logging.getLogger("carbon_ledger.reranker")

class DocumentReranker:
    def __init__(self):
        logger.info("Loading local FlashRank Cross-Encoder engine into memory...")
        # Initializes the highly efficient, lightweight ms-marco-MiniLM-L-6-v2 model by default
        self.ranker = Ranker()
        logger.info("FlashRank engine successfully armed.")

    def rerank(self, query: str, candidate_documents: list[dict], top_n: int = 4) -> list[dict]:
        """
        Takes raw database results and re-scores them relative to the search query.
        Returns the top_n most contextually accurate matching structures.
        """
        if not candidate_documents:
            return []

        # Re-map our list dict format into standard FlashRank payload targets
        flash_docs = [
            {
                "id": str(doc["id"]),
                "text": doc["raw_text_chunk"],
                "meta": {
                    "framework_name": doc["framework_name"],
                    "section_identifier": doc["section_identifier"]
                }
            }
            for doc in candidate_documents
        ]

        rerank_request = RerankRequest(query=query, passages=flash_docs)
        results = self.ranker.rerank(rerank_request)

        # Truncate and return the highest-scoring documents
        final_selections = results[:top_n]
        logger.info(f"Reranked {len(candidate_documents)} entries down to {len(final_selections)} premium context blocks.")
        return final_selections

# Singleton instance
document_reranker = DocumentReranker()