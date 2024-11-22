from openai import OpenAI
import logging
from typing import List, Dict
import uuid
import pinecone
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class VectorService:
    def __init__(self, api_key: str, environment: str, index_name: str, host: str = None):
        try:
            # Initialize Pinecone
            pinecone.init(
                api_key=api_key,
                environment=environment
            )
            
            # Get or create index
            if index_name not in pinecone.list_indexes():
                pinecone.create_index(
                    name=index_name,
                    dimension=1536,  # OpenAI embeddings dimension
                    metric='cosine'
                )
                logger.info(f"Created new Pinecone index: {index_name}")
            
            # Connect to index - Updated for new Pinecone SDK
            if host:
                self.pinecone_index = pinecone.Index(
                    host=host
                )
            else:
                self.pinecone_index = pinecone.Index(
                    host=f"https://{index_name}-{environment}.svc.{environment}.pinecone.io"
                )
            logger.info(f"Connected to Pinecone index: {index_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone index: {str(e)}")
            raise e

    def store_embedding(self, text: str, metadata: dict) -> bool:
        """Store text embedding in vector database"""
        try:
            if not self.pinecone_index:
                logger.warning("Vector service not available for storage")
                return False

            # Generate embedding
            embedding = self._get_embedding(text)
            
            # Store in Pinecone
            self.pinecone_index.upsert(
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

    def search(self, vector: List[float], top_k: int = 5) -> List[Dict]:
        try:
            results = self.pinecone_index.query(
                vector=vector,
                top_k=top_k,
                include_metadata=True
            )
            return results.matches
        except Exception as e:
            logger.error(f"Error searching vectors: {str(e)}")
            raise e

    def upsert(self, vectors, metadata=None):
        try:
            self.pinecone_index.upsert(vectors=vectors, metadata=metadata)
            return True
        except Exception as e:
            logger.error(f"Error upserting vectors: {str(e)}")
            return False