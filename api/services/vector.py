import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class VectorService:
    def __init__(self, pinecone_index):
        self.index = pinecone_index

    def store_vector(self, 
                    text: str, 
                    embedding: list[float], 
                    metadata: Dict[str, Any]) -> Optional[str]:
        """Store a vector in Pinecone"""
        try:
            vector_id = f"thought_{datetime.utcnow().isoformat()}"
            vector_record = {
                'id': vector_id,
                'values': embedding,
                'metadata': {
                    'text': text,
                    'timestamp': datetime.utcnow().isoformat(),
                    **metadata
                }
            }
            
            self.index.upsert(vectors=[vector_record])
            logger.info(f"Stored vector with ID: {vector_id}")
            return vector_id
            
        except Exception as e:
            logger.error(f"Failed to store vector: {str(e)}")
            return None

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