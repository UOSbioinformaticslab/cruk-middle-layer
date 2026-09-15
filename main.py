import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from database import engine
import models
from routers import team_requests, logs, enquiries, tours

# Create the database tables automatically
models.Base.metadata.create_all(bind=engine)

# Ensure Option 1 upload directory exists
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads/audio")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(
    title="CRUK Middlelayer API",
    description="Microservice for CRUK specific data storage and operations separate from HDRUK",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Option 1 Static File Storage
app.mount("/static/audio", StaticFiles(directory=UPLOAD_DIR), name="static_audio")

app.include_router(team_requests.router)
app.include_router(logs.router)
app.include_router(enquiries.router)
app.include_router(tours.router)
