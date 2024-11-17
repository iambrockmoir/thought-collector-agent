from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "API is running"}

@app.post("/webhook")
async def webhook(request: Request):
    try:
        form = await request.form()
        
        # Log incoming request for debugging
        print(f"Received webhook: {dict(form)}")
        
        # Create TwiML response
        twiml_response = """<?xml version="1.0" encoding="UTF-8"?>
                           <Response>
                               <Message>Message received!</Message>
                           </Response>"""
        
        return Response(
            content=twiml_response,
            media_type="application/xml"
        )
    except Exception as e:
        print(f"Error in webhook: {str(e)}")
        return Response(
            content="Error processing webhook",
            status_code=500
        )