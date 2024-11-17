from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, PlainTextResponse
from fastapi.security import HTTPBasic
from starlette.exceptions import HTTPException

app = FastAPI()
security = HTTPBasic(auto_error=False)

@app.post("/webhook")
async def webhook(request: Request):
    try:
        form_data = await request.form()
        message_body = form_data.get('Body', '')
        from_number = form_data.get('From', '')
        
        print(f"Received message: {message_body} from {from_number}")
        
        # Return a simple TwiML response
        twiml = """<?xml version="1.0" encoding="UTF-8"?>
                  <Response>
                      <Message>Message received!</Message>
                  </Response>"""
        
        return Response(content=twiml, media_type="application/xml")
    except Exception as e:
        print(f"Error in webhook: {str(e)}")
        return PlainTextResponse(
            content=f"Error: {str(e)}",
            status_code=500
        )

@app.get("/")
async def root():
    return {"message": "API is running"}