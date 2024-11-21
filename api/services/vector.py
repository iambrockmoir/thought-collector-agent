from openai import OpenAI
import logging
from typing import List, Dict
import uuid

logger = logging.getLogger(__name__)

class VectorService:
    def __init__(self, openai_client, pinecone_index):
        self.openai = openai_client
        self.index = pinecone_index
        logger.info(f"VectorService initialized with Pinecone index")
        if pinecone_index:
            stats = pinecone_index.describe_index_stats()
            logger.info(f"Pinecone index stats: {stats}")

    def store_embedding(self, text: str, metadata: dict) -> bool:
        """Store text embedding in vector database"""
        try:
            if not self.index:
                logger.warning("Vector service not available for storage")
                return False

            # Generate embedding
            embedding = self._get_embedding(text)
            
            # Store in Pinecone
            self.index.upsert(
                vectors=[{
                    'id': str(uuid.uuid4()),
                    'values': embedding,
                    'metadata': metadata
                }]
            )
            
            return True

        except Exception as e:
            logger.error(f"Failed to store embedding: {str(e)}")
            return False

    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text using OpenAI"""
        try:
            response = self.openai.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to get embedding: {str(e)}")
            raise

    def search(self, query: str, limit: int = 5) -> List[dict]:
        """Search for similar vectors"""
        try:
            # Generate query embedding
            response = self.openai.embeddings.create(
                model="text-embedding-ada-002",
                input=query
            )
            query_embedding = response.data[0].embedding
            
            # Search Pinecone
            results = self.index.query(
                vector=query_embedding,
                top_k=limit,
                include_metadata=True
            )
            return results.matches
        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            return []