from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from twilio.twiml.messaging_response import MessagingResponse
from api.chat import ChatEngine
from api.transcription import AudioProcessor

app = FastAPI()
chat_engine = ChatEngine()
audio_processor = AudioProcessor()

@app.post("/webhook")
async def handle_webhook(request: Request):
    try:
        # Parse the incoming webhook
        form = await request.form()
        
        # Print incoming request
        print("DEBUG: Received webhook data:", dict(form))
        
        # Get the message body and media URL
        message_body = form.get("Body", "")
        media_url = form.get("MediaUrl0")
        user_phone = form.get("From", "")
        
        print(f"DEBUG: Processing message: '{message_body}' from {user_phone}")
        
        # Handle audio message
        if media_url:
            try:
                result = await audio_processor.process_audio_message(
                    media_url=media_url,
                    user_phone=user_phone
                )
                print("DEBUG: Audio processing result:", result)
                return create_twiml_response(result["message"])
            except Exception as e:
                print(f"ERROR: Audio processing failed: {str(e)}")
                return create_twiml_response("Sorry, I couldn't process that audio. Please try again.")
        
        # Handle text message
        elif message_body:
            try:
                print("DEBUG: About to process chat query")
                response = await chat_engine.process_query(
                    user_phone=user_phone,
                    message=message_body
                )
                print("DEBUG: Chat response:", response)
                return create_twiml_response(response["response"])
            except Exception as e:
                print(f"ERROR: Chat processing failed: {str(e)}")
                return create_twiml_response("Sorry, I couldn't process that message. Please try again.")
            
        else:
            return create_twiml_response("Please send a text or audio message.")
            
    except Exception as e:
        print(f"ERROR: Webhook failed: {str(e)}")
        return create_twiml_response("Sorry, something went wrong. Please try again.")

def create_twiml_response(message: str) -> str:
    response = MessagingResponse()
    response.message(message)
    print("DEBUG: Sending response:", str(response))
    return str(response)