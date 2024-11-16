from fastapi import FastAPI, Request
from api.chat import ChatEngine
from api.transcription import AudioProcessor
from lib.database import Database

app = FastAPI()
chat_engine = ChatEngine()
audio_processor = AudioProcessor()
database = Database()

@app.post("/sms")
async def handle_webhook(request: Request):
    form = await request.form()
    
    # Handle audio message
    if "MediaUrl0" in form:
        result = await audio_processor.process_audio_message(
            media_url=form["MediaUrl0"],
            user_phone=form["From"]
        )
        return create_twiml_response(result["message"])
    
    # Handle text message
    else:
        response = await chat_engine.process_query(
            user_phone=form["From"],
            message=form["Body"]
        )
        return create_twiml_response(response["response"])