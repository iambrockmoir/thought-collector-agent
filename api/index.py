from fastapi import FastAPI
import uvicorn
from routes import app

# This is for local development
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)