from typing import List
from openai import OpenAI
from .storage import StorageService
from .vector import VectorService
import logging

logger = logging.getLogger(__name__)

class TagService:
    def __init__(self, storage_service: StorageService, vector_service: VectorService):
        self.storage = storage_service
        self.vector = vector_service
        self.openai_client = OpenAI()

    async def suggest_tags(self, transcription: str, user_phone: str) -> List[str]:
        """Generate tag suggestions for a transcribed thought."""
        try:
            existing_tags = await self.storage.get_existing_tags(user_phone)
            logger.info(f"Found existing tags: {existing_tags}")
            
            prompt = f"""
            Analyze this transcription and suggest relevant tags.
            Existing tags: {existing_tags}
            Transcription: {transcription}
            
            Return only the most relevant tags as a comma-separated list, preferring existing tags when appropriate.
            Limit to 5 most relevant tags.
            """
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{
                    "role": "system",
                    "content": "You are a helpful assistant that suggests relevant tags for thoughts. Return only the comma-separated list of tags, nothing else."
                }, {
                    "role": "user",
                    "content": prompt
                }]
            )
            
            if not response.choices or not response.choices[0].message.content:
                logger.warning("No tag suggestions generated")
                return []
                
            suggested_tags = response.choices[0].message.content.strip()
            logger.info(f"Raw tag suggestions: {suggested_tags}")
            
            if not suggested_tags:
                return []
                
            tags = [tag.strip() for tag in suggested_tags.split(",") if tag.strip()]
            logger.info(f"Processed tag suggestions: {tags}")
            return tags
            
        except Exception as e:
            logger.error(f"Failed to generate tag suggestions: {str(e)}")
            logger.error(f"Traceback: {e.__traceback__}")
            return []

    async def process_tag_confirmation(self, user_tags: str) -> List[str]:
        """Process user-confirmed tags from comma-separated string."""
        if not user_tags:
            return []
            
        # Split and clean tags
        tags = [tag.strip().lower() for tag in user_tags.split(",")]
        
        # Remove empty tags and duplicates
        tags = list(set(filter(None, tags)))
        
        return tags

    async def store_thought_tags(self, thought_id: str, tags: List[str], user_phone: str):
        """Store tags for a thought in both Supabase and Pinecone."""
        # Store in Supabase
        await self.storage.store_tags(thought_id, tags, user_phone)
        
        # Update Pinecone metadata
        metadata = {"tags": tags}
        await self.vector.update_metadata(thought_id, metadata) 