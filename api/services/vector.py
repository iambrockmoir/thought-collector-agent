from openai import OpenAI
import logging
from typing import List, Dict
import uuid

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

    def store_embedding(self, text: str, metadata: dict = None) -> bool:
        """Store text embedding in Pinecone"""
        try:
            # Generate embedding using OpenAI
            response = self.client.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            embedding = response.data[0].embedding
            
            # Store in Pinecone with metadata
            self.index.upsert(
                vectors=[{
                    'id': str(uuid.uuid4()),
                    'values': embedding,
                    'metadata': metadata or {}
                }]
            )
            return True
        except Exception as e:
            logger.error(f"Failed to store embedding: {str(e)}")
            return False

    def search(self, query: str, limit: int = 5) -> List[dict]:
        """Search for similar vectors"""
        try:
            # Generate query embedding
            response = self.client.embeddings.create(
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