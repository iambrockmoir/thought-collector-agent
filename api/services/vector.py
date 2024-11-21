from openai import OpenAI
import logging
from typing import List, Dict
import uuid
import pinecone

logger = logging.getLogger(__name__)

class VectorService:
    def __init__(self, api_key: str, environment: str, index_name: str, host: str):
        # Initialize with the classic method
        pinecone.init(
            api_key=api_key,
            environment=environment
        )
        
        # Connect to index
        self.index = pinecone.Index(index_name)
        logger.info("VectorService initialized with Pinecone index")

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

    def search(self, query_vector, top_k=5):
        try:
            results = self.index.query(
                vector=query_vector,
                top_k=top_k,
                include_metadata=True
            )
            return results
        except Exception as e:
            logger.error(f"Error searching vectors: {str(e)}")
            return None

    def upsert(self, vectors, metadata=None):
        try:
            self.index.upsert(vectors=vectors, metadata=metadata)
            return True
        except Exception as e:
            logger.error(f"Error upserting vectors: {str(e)}")
            return False