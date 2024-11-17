 from fastapi import FastAPI, Request
from fastapi.responses import Response

app = FastAPI()

@app.post("/")
async def twilio_webhook(request: Request):
    try:
        form_data = await request.form()
        message_body = form_data.get('Body', '')
        from_number = form_data.get('From', '')
        
        print(f"Received message: {message_body} from {from_number}")
        
        twiml = """<?xml version="1.0" encoding="UTF-8"?>
                  <Response>
                      <Message>Message received!</Message>
                  </Response>"""
        
        return Response(content=twiml, media_type="application/xml")
    except Exception as e:
        print(f"Error in webhook: {str(e)}")
        return Response(
            content=f"Error: {str(e)}",
            status_code=500
        )

@app.get("/health")
async def health_check():
    return {"status": "healthy"}