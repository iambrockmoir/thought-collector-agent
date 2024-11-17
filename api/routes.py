from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from twilio.twiml.messaging_response import MessagingResponse
from api.chat import ChatEngine
from api.transcription import AudioProcessor
from lib.database import Database

app = FastAPI()
chat_engine = ChatEngine()
audio_processor = AudioProcessor()
database = Database()

@app.post("/webhook")
async def handle_webhook(request: Request):
    try:
        # Parse the incoming webhook
        form = await request.form()
        
        # Get the message body and media URL
        message_body = form.get("Body", "")
        media_url = form.get("MediaUrl0")
        user_phone = form.get("From")
        
        # Handle audio message
        if media_url:
            result = await audio_processor.process_audio_message(
                media_url=media_url,
                user_phone=user_phone
            )
            return create_twiml_response(result["message"])
        
        # Handle text message
        elif message_body:
            response = await chat_engine.process_query(
                user_phone=user_phone,
                message=message_body
            )
            return create_twiml_response(response["response"])
            
        else:
            return create_twiml_response("Please send a text or audio message.")
            
    except Exception as e:
        print(f"Error in webhook: {str(e)}")  # For logging
        return create_twiml_response("Sorry, something went wrong. Please try again.")

def create_twiml_response(message: str) -> str:
    response = MessagingResponse()
    response.message(message)
    return str(response)

@app.get("/")
async def root():
    return {"message": "API is running"}