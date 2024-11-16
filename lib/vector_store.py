from typing import Dict, List, Any
import pinecone
from lib.config import get_settings
from lib.error_handler import AppError

settings = get_settings()

class PineconeClient:
    def __init__(self):
        # Initialize Pinecone
        self.pc = Pinecone(
            api_key=settings.pinecone_api_key,
            host=settings.pinecone_environment
        )
        self.index_name = "thoughts-index"
        self.index = self.pc.Index(self.index_name)
        self.dimension = 1536  # OpenAI embedding dimension
        self.metric = "cosine"  # Similarity metric

    async def initialize_index(self) -> None:
        """Ensure index exists with correct configuration"""
        try:
            if self.index_name not in self.pc.list_indexes():
                self.pc.create_index(
                    name=self.index_name,
                    dimension=self.dimension,
                    metric=self.metric
                )
        except Exception as e:
            raise AppError(f"Pinecone index creation error: {str(e)}")

    async def store_embedding(
        self,
        thought_id: str,
        embedding: List[float],
        metadata: Dict[str, Any]
    ) -> None:
        """Store embedding in Pinecone"""
        try:
            self.index.upsert(
                vectors=[{
                    'id': thought_id,
                    'values': embedding,
                    'metadata': metadata
                }]
            )
        except Exception as e:
            raise AppError(f"Pinecone storage error: {str(e)}", status_code=500)

    async def similarity_search(
        self,
        query_embedding: List[float],
        filter: Dict[str, Any] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors in Pinecone"""
        try:
            results = self.index.query(
                vector=query_embedding,
                filter=filter,
                top_k=limit,
                include_metadata=True
            )
            return [
                {
                    'id': match.id,
                    'score': match.score,
                    'metadata': match.metadata
                }
                for match in results.matches
            ]
        except Exception as e:
            raise AppError(f"Pinecone search error: {str(e)}", status_code=500)