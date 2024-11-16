from pinecone import Pinecone, ServerlessSpec
from lib.config import get_settings

def init_pinecone():
    """Initialize Pinecone index for thought vectors"""
    try:
        settings = get_settings()
        pc = Pinecone(api_key=settings.pinecone_api_key)
        
        # Check if index already exists
        existing_indexes = pc.list_indexes()
        if "thoughts-index" not in existing_indexes:
            print("Creating new Pinecone index 'thoughts-index'...")
            pc.create_index(
                name="thoughts-index",
                dimension=1536,  # OpenAI embedding dimension
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-west-2"
                )
            )
            print("Index created successfully!")
        else:
            print("Index 'thoughts-index' already exists.")
            
    except Exception as e:
        print(f"Error initializing Pinecone: {str(e)}")
        raise

if __name__ == "__main__":
    init_pinecone()