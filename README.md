# Thought Chat

An SMS-based thought collection and chat system that allows users to record thoughts via voice messages and interact with them through text conversations.

## Setup

1. Clone the repository 

bash
git clone https://github.com/yourusername/thought-collector-agent.git
cd thought--collector-agent

2. Create and activate virtual environment

bash
python -m venv venv
source venv/bin/activate # On Windows: venv\Scripts\activate

3. Install dependencies

bash
pip install -r requirements.txt

4. Copy .env.example to .env and fill in your credentials

bash
cp .env.example .env

5. Run the application

bash
python src/main.py

## Development

- Built with Flask, Firebase, and Pinecone
- Uses OpenAI for audio transcription and chat
- Twilio for SMS handling

## Deployment

The application is designed to be deployed on Replit. See deployment documentation for details.