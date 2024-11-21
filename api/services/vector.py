import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

class VectorService:
    def __init__(self, openai_client: OpenAI, pinecone_index):
        self.client = openai_client
        self.index = pinecone_index
        logger.info("VectorService initialized with Pinecone index")
        logger.info(f"Pinecone index stats: {self.index.describe_index_stats()}")

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI"""
        try:
            response = self.client.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)}")
            return []

    def store_vector(self, id: str, vector: List[float], metadata: Dict = None):
        """Store vector in Pinecone"""
        try:
            self.index.upsert(
                vectors=[{
                    'id': id,
                    'values': vector,
                    'metadata': metadata or {}
                }]
            )
            return True
        except Exception as e:
            logger.error(f"Failed to store vector: {str(e)}")
            return False

    def query_vectors(self, 
                     query_embedding: list[float], 
                     top_k: int = 5) -> list[Dict[str, Any]]:
        """Query similar vectors from Pinecone"""
        try:
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True
            )
            return results.matches
            
        except Exception as e:
            logger.error(f"Failed to query vectors: {str(e)}")
            return [] 