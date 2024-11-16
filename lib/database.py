from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4
from supabase import create_client, Client
from pinecone import Pinecone

from lib.config import get_settings
from lib.error_handler import AppError

settings = get_settings()

class Database:
    def __init__(self):
        # Initialize Supabase with minimal options
        self.supabase: Client = create_client(
            supabase_url=settings.supabase_url,
            supabase_key=settings.supabase_key,
            options={
                'auth': {
                    'autoRefreshToken': True,
                    'persistSession': False
                }
            }
        )
        
        # Initialize Pinecone
        self.pinecone = Pinecone(
            api_key=settings.pinecone_api_key,
            environment=settings.pinecone_environment
        )
        
        self.CACHE_TIMEOUT = 300  # 5 minutes
        self._thought_cache = {}

    async def store_thought(self, thought_data: Dict[str, Any]) -> Dict[str, Any]:
        """Store thought in both Supabase and Pinecone"""
        try:
            # Generate UUID for the thought
            thought_id = str(uuid4())
            
            # Generate embedding for the thought
            embedding = await self._generate_embedding(thought_data['transcription'])
            
            # Prepare Supabase record
            supabase_record = {
                'id': thought_id,
                'user_phone': thought_data['user_phone'],
                'audio_url': thought_data['audio_url'],
                'transcription': thought_data['transcription'],
                'created_at': datetime.utcnow().isoformat(),
                'metadata': thought_data.get('metadata', {})
            }

            # Store in Supabase
            db_response = await self.supabase.table('thoughts').insert(supabase_record).execute()
            
            # Store in Pinecone
            await self.pinecone.Index("thoughts").upsert(
                vectors=[{
                    'id': thought_id,
                    'values': embedding,
                    'metadata': {
                        'user_phone': thought_data['user_phone'],
                        'transcription': thought_data['transcription']
                    }
                }]
            )

            return db_response.data[0]

        except Exception as e:
            raise AppError(f"Database storage error: {str(e)}", status_code=500)

    async def search_thoughts(
        self,
        user_phone: str,
        query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for relevant thoughts using vector similarity"""
        try:
            # Generate embedding for query
            query_embedding = await self._generate_embedding(query)
            
            # Search Pinecone for similar thoughts
            similar_thoughts = await self.pinecone.similarity_search(
                query_embedding,
                filter={'user_phone': user_phone},
                limit=limit
            )
            
            # Get full thought records from Supabase
            thought_ids = [thought['id'] for thought in similar_thoughts]
            thoughts = await self.supabase.table('thoughts')\
                .select('*')\
                .in_('id', thought_ids)\
                .execute()

            return thoughts.data

        except Exception as e:
            raise AppError(f"Thought search error: {str(e)}", status_code=500)

    async def get_thought_by_id(self, thought_id: UUID) -> Optional[Dict[str, Any]]:
        """Retrieve a specific thought by ID"""
        try:
            cache_key = str(thought_id)
            if cache_key in self._thought_cache:
                cached = self._thought_cache[cache_key]
                if (datetime.utcnow() - cached['timestamp']).seconds < self.CACHE_TIMEOUT:
                    return cached['data']

            response = await self.supabase.table('thoughts')\
                .select('*')\
                .eq('id', str(thought_id))\
                .single()\
                .execute()
            return response.data

        except Exception as e:
            raise AppError(f"Error retrieving thought: {str(e)}", status_code=500)

    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI API"""
        try:
            response = await self.supabase.functions.invoke(
                'generate-embedding',
                invoke_options={'body': {'text': text}}
            )
            return response['embedding']
        except Exception as e:
            raise AppError(f"Embedding generation error: {str(e)}", status_code=500)