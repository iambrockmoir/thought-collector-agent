from fastapi import FastAPI, Request
from fastapi.responses import Response
from twilio.twiml.messaging_response import MessagingResponse
from api.chat import ChatEngine
from api.transcription import AudioProcessor

app = FastAPI()
chat_engine = ChatEngine()
audio_processor = AudioProcessor()

@app.post("/webhook")
async def handle_webhook(request: Request):
    try:
        form = await request.form()
        print("DEBUG: Received webhook data:", dict(form))
        
        message_body = form.get("Body", "")
        media_url = form.get("MediaUrl0")
        user_phone = form.get("From", "")
        
        print(f"DEBUG: Processing message: '{message_body}' from {user_phone}")
        
        # Create TwiML response
        twiml = MessagingResponse()
        
        if media_url:
            try:
                result = await audio_processor.process_audio_message(
                    media_url=media_url,
                    user_phone=user_phone
                )
                twiml.message(result["message"])
            except Exception as e:
                print(f"ERROR: Audio processing failed: {str(e)}")
                twiml.message("Sorry, I couldn't process that audio. Please try again.")
        
        elif message_body:
            try:
                response = await chat_engine.process_query(
                    user_phone=user_phone,
                    message=message_body
                )
                twiml.message(response["response"])
            except Exception as e:
                print(f"ERROR: Chat processing failed: {str(e)}")
                twiml.message("Sorry, I couldn't process that message. Please try again.")
        
        else:
            twiml.message("Please send a text or audio message.")
        
        # Return response with correct content type
        twiml_str = str(twiml)
        print("DEBUG: Sending TwiML:", twiml_str)
        
        return Response(
            content=twiml_str,
            media_type="application/xml",
            headers={"Content-Type": "application/xml; charset=utf-8"}
        )
            
    except Exception as e:
        print(f"ERROR: Webhook failed: {str(e)}")
        twiml = MessagingResponse()
        twiml.message("Sorry, something went wrong. Please try again.")
        return Response(
            content=str(twiml),
            media_type="application/xml",
            headers={"Content-Type": "application/xml; charset=utf-8"}
        )