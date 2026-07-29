from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine
import models
from routers import team_requests

# Create the database tables automatically
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="CRUK Middlelayer API",
    description="Microservice for CRUK specific data storage and operations separate from HDRUK",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173",
                   "https://crukdatahub-staging.up.railway.app",
                   "https://crukdatahub-production.up.railway.app",
                   "https://crukdatahublandingpage-production.up.railway.app",
                   "https://crukdatahublandingpage-staging.up.railway.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(team_requests.router)



