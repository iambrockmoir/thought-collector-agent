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

        # Add OpenAI client initialization
        self.openai_client = OpenAI()

    async def store_embedding(self, text: str, metadata: dict, phone_number: str) -> bool:
        """Store text embedding in vector database with user's phone number"""
        try:
            if not self.pinecone_index:
                logger.warning("Vector service not available for storage")
                return False

            # Generate embedding
            embedding = await self._get_embedding(text)
            
            # Add phone number to metadata
            metadata['phone_number'] = phone_number
            
            # Store in Pinecone
            await self.pinecone_index.upsert(
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

    async def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text using OpenAI"""
        try:
            response = await self.openai_client.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            if not response.data:
                raise Exception("No embedding data returned from OpenAI")
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to get embedding: {str(e)}")
            raise

    async def search(self, query: str, phone_number: str, limit: int = 5) -> List[Dict]:
        try:
            # 1. Convert query to embedding vector
            embedding = await self._get_embedding(query)
            
            # 2. Search Pinecone for similar vectors with phone number filter
            results = await self.pinecone_index.query(
                vector=embedding,
                top_k=limit,
                include_metadata=True,
                filter={"phone_number": {"$eq": phone_number}}
            )
            return results.matches
        except Exception as e:
            logger.error(f"Error searching vectors: {str(e)}")
            raise

    async def get_embedding(self, text: str) -> List[float]:
        """Get embeddings for a text string using OpenAI"""
        try:
            # Use the internal _get_embedding method for consistency
            return await self._get_embedding(text)
        except Exception as e:
            logger.error(f"Error getting embedding: {str(e)}")
            raise

    async def upsert(self, vectors, metadata=None):
        """Upsert vectors to Pinecone"""
        try:
            await self.pinecone_index.upsert(vectors=vectors, metadata=metadata)
            return True
        except Exception as e:
            logger.error(f"Error upserting vectors: {str(e)}")
            return False

    async def update_metadata(self, thought_id: str, metadata_update: Dict) -> bool:
        """Update metadata for a specific vector."""
        try:
            # Get current vector and metadata
            vector_data = self.pinecone_index.fetch(ids=[thought_id])
            
            if not vector_data.vectors:
                logger.error(f"Vector not found for thought_id: {thought_id}")
                return False
                
            # Merge existing metadata with updates
            current_metadata = vector_data.vectors[thought_id].metadata
            updated_metadata = {**current_metadata, **metadata_update}
            
            # Update vector with new metadata
            self.pinecone_index.update(
                id=thought_id,
                metadata=updated_metadata
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update vector metadata: {str(e)}")
            return False