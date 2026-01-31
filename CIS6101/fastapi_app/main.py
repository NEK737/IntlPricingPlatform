from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_app.routers import chat, facilities


app = FastAPI(title="Food Safety AI API", version="1.0")

# Allow frontend (React/Streamlit/Flask UI) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(facilities.router, prefix="/api", tags=["Facilities"])
