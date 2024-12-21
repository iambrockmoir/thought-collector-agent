import asyncio
from api.services.vector import VectorService

async def test_vector_service():
    # Initialize service with your credentials
    vector_service = VectorService(
        api_key="pcsk_eVUiQ_BF94A5jcwdT93wVCNSxx3SxN1Ncvwt9iWRezY4hWVYAUxkbqMrrFLN5LSHjuwUc",
        index_name="thoughts-index",
        host="https://thoughts-index-qt78i74.svc.aped-4627-b74a.pinecone.io"
    )
    
    # Test phone numbers
    phone1 = "+1111111111"
    phone2 = "+2222222222"
    
    # Store memories for two different users
    print("\nStoring memories...")
    vector_service.store_embedding(
        text="This is user 1s memory about pizza",
        metadata={"type": "memory"},
        phone_number=phone1
    )
    
    vector_service.store_embedding(
        text="This is user 2s memory about ice cream",
        metadata={"type": "memory"},
        phone_number=phone2
    )
    
    # Search for memories
    print("\nSearching for user 1s memories...")
    results1 = await vector_service.search("food", phone_number=phone1)
    print(f"User 1 results: {results1}")
    
    print("\nSearching for user 2s memories...")
    results2 = await vector_service.search("food", phone_number=phone2)
    print(f"User 2 results: {results2}")

if __name__ == "__main__":
    asyncio.run(test_vector_service()) 