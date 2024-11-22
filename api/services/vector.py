from openai import OpenAI
import logging
from typing import List, Dict
import uuid
from pinecone import Pinecone
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class VectorService:
    def __init__(self, api_key: str, index_name: str, host: str):
        try:
            logger.info(f"Initializing Pinecone for index: {index_name}")
            
            # Initialize with new API
            pc = Pinecone(api_key=api_key)
            logger.info("Pinecone core initialized successfully")
            
            # Get index using new API
            logger.info(f"Connecting to index: {index_name}")
            self.pinecone_index = pc.Index(index_name)
            
            # Verify connection
            try:
                stats = self.pinecone_index.describe_index_stats()
                logger.info(f"Successfully connected to index. Stats: {stats}")
            except Exception as e:
                logger.error(f"Failed to get index stats: {str(e)}")
                raise e
            
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone index: {str(e)}")
            logger.error(f"API Key (first 8 chars): {api_key[:8]}...")
            logger.error(f"Index Name: {index_name}")
            logger.error(f"Host: {host}")
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

    async def search(self, query: str, limit: int = 5) -> List[Dict]:
        try:
            # First get embeddings for the query text
            embedding = await self.get_embedding(query)
            
            # Then search using the embedding vector
            results = self.pinecone_index.query(
                vector=embedding,
                top_k=limit,
                include_metadata=True
            )
            
            logger.info(f"Found {len(results.matches)} matching thoughts")
            return [match.metadata for match in results.matches]
            
        except Exception as e:
            logger.error(f"Error searching vectors: {str(e)}")
            raise

    async def get_embedding(self, text: str) -> List[float]:
        """Get embeddings for a text string using OpenAI"""
        try:
            response = await openai.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error getting embedding: {str(e)}")
            raise

    def upsert(self, vectors, metadata=None):
        try:
            self.pinecone_index.upsert(vectors=vectors, metadata=metadata)
            return True
        except Exception as e:
            logger.error(f"Error upserting vectors: {str(e)}")
            return False