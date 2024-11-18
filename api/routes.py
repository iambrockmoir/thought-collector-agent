from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI without trying to load other services initially
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
async def health_check():
    """Health check endpoint"""
    try:
        return {
            "status": "healthy",
            "message": "ThoughtCollector API is running",
            "version": "1.0.0"
        }
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
    """Debug endpoint to check environment"""
    try:
        return {
            "python_version": sys.version,
            "endpoints": [
                {"path": "/", "methods": ["GET"]},
                {"path": "/debug", "methods": ["GET"]}
            ]
        }
    except Exception as e:
        logger.error(f"Debug info failed: {str(e)}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )