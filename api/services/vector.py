from openai import OpenAI
import logging
from typing import List, Dict
import uuid
import pinecone
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class VectorService:
    def __init__(self, api_key: str, environment: str, index_name: str, host: str):
        # Extract the domain from the host URL
        parsed_url = urlparse(host)
        domain = parsed_url.netloc.split('.')[0]  # Get the first part of the domain
        
        # Initialize Pinecone with the correct environment
        pinecone.init(
            api_key=api_key,
            environment=environment
        )
        
        try:
            # Connect to index
            self.index = pinecone.Index(
                name=index_name
            )
            logger.info(f"VectorService initialized with Pinecone index: {index_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone index: {str(e)}")
            raise e

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