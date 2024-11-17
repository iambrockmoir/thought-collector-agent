from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from twilio.twiml.messaging_response import MessagingResponse

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "API is running"}

@app.post("/webhook")
async def handle_webhook(request: Request):
    try:
        # Parse the incoming webhook
        form = await request.form()
        
        # Get basic info
        message_body = form.get("Body", "")
        user_phone = form.get("From", "")
        
        # Simple response
        return create_twiml_response(f"Received: {message_body} from {user_phone}")
            
    except Exception as e:
        print(f"Error in webhook: {str(e)}")  # For logging
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

def create_twiml_response(message: str) -> str:
    response = MessagingResponse()
    response.message(message)
    return str(response)