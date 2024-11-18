from fastapi import FastAPI, Request
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from twilio.twiml.messaging_response import MessagingResponse
from api.chat import ChatEngine
from api.transcription import AudioProcessor
import logging
import sys

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI with error handling
app = FastAPI(
    title="ThoughtCollector API",
    description="API for processing audio thoughts and chat interactions",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    chat_engine = ChatEngine()
    audio_processor = AudioProcessor()
    logger.info("Successfully initialized ChatEngine and AudioProcessor")
except Exception as e:
    logger.error(f"Failed to initialize services: {str(e)}")
    raise

@app.get("/")
async def health_check():
    """Health check endpoint"""
    try:
        return JSONResponse(
            content={
                "status": "healthy",
                "message": "ThoughtCollector API is running",
                "version": "1.0.0"
            },
            status_code=200
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            content={
                "status": "error",
                "message": str(e)
            },
            status_code=500
        )

@app.get("/debug")
async def debug_info():
    """Debug endpoint to check environment and initialization"""
    try:
        return JSONResponse({
            "python_version": sys.version,
            "chat_engine_initialized": chat_engine is not None,
            "audio_processor_initialized": audio_processor is not None,
            "endpoints": [
                {"path": "/", "methods": ["GET"]},
                {"path": "/api/sms", "methods": ["POST"]},
                {"path": "/debug", "methods": ["GET"]}
            ]
        })
    except Exception as e:
        logger.error(f"Debug info failed: {str(e)}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )

@app.post("/api/sms")
async def handle_sms_webhook(request: Request):
    try:
        form = await request.form()
        logger.info(f"Received webhook data: {dict(form)}")
        
        message_body = form.get("Body", "")
        media_url = form.get("MediaUrl0")
        user_phone = form.get("From", "")
        
        logger.info(f"Processing message: '{message_body}' from {user_phone}")
        
        twiml = MessagingResponse()
        
        if media_url:
            try:
                result = await audio_processor.process_audio_message(
                    media_url=media_url,
                    user_phone=user_phone
                )
                twiml.message(result["message"])
            except Exception as e:
                logger.error(f"Audio processing failed: {str(e)}")
                twiml.message("Sorry, I couldn't process that audio. Please try again.")
        
        elif message_body:
            try:
                response = await chat_engine.process_query(
                    user_phone=user_phone,
                    message=message_body
                )
                twiml.message(response["response"])
            except Exception as e:
                logger.error(f"Chat processing failed: {str(e)}")
                twiml.message("Sorry, I couldn't process that message. Please try again.")
        
        else:
            twiml.message("Please send a text or audio message.")
        
        twiml_str = str(twiml)
        logger.info(f"Sending TwiML: {twiml_str}")
        
        return Response(
            content=twiml_str,
            media_type="application/xml",
            headers={"Content-Type": "application/xml; charset=utf-8"}
        )
            
    except Exception as e:
        logger.error(f"Webhook failed: {str(e)}")
        twiml = MessagingResponse()
        twiml.message("Sorry, something went wrong. Please try again.")
        return Response(
            content=str(twiml),
            media_type="application/xml",
            headers={"Content-Type": "application/xml; charset=utf-8"}
        )

@app.post("/webhook")
async def legacy_webhook(request: Request):
    """Redirect old webhook endpoint to new one"""
    return await handle_sms_webhook(request)