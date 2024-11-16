import asyncio
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

from dotenv import load_dotenv
from api.chat import ChatEngine

# Load environment variables
load_dotenv()

async def test_chat():
    chat_engine = ChatEngine()
    
    # Simulate a conversation
    user_phone = "+17802036982"
    messages = [
        "Hello, can you help me find my thoughts about work?",
        "What did I say about meetings yesterday?",
        "Thank you!"
    ]
    
    for message in messages:
        print(f"\nUser: {message}")
        try:
            response = await chat_engine.process_query(user_phone, message)
            print(f"Assistant: {response}")
        except Exception as e:
            print(f"Error: {str(e)}")

if __name__ == "__main__":
    # Ensure you have OPENAI_API_KEY in your .env file
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not found in environment variables")
    else:
        asyncio.run(test_chat())