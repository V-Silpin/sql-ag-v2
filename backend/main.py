import os
from fastapi import FastAPI
from api.routes import router
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from dotenv import load_dotenv

# ✅ Safely load environment variables from .env if present
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

app = FastAPI()

# Allow all origins (or specify your allowed domains)
origins = ["*"]

@app.get("/api/health-check")
async def health_check():
    """
    This route returns a 200 OK response, indicating that the health check endpoint is working.
    """
    return JSONResponse(content={"status": "ok"}, status_code=200)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,          # Allows all origins if set to ["*"]
    allow_credentials=True,
    allow_methods=["POST"],         # Allows POST requests (adjust if needed)
    allow_headers=["*"],            # Allows all headers
)

# Include routes
app.include_router(router, prefix="")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8003))
    uvicorn.run(app, host="0.0.0.0", port=port)