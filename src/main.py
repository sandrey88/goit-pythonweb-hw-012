from fastapi import FastAPI
from .routes import contacts, users
from src.database.db import engine
from src.database.models import Base
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from src.limiter import limiter

app = FastAPI(title="Contacts API")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

origins = [
    "http://localhost:3000"
]

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(contacts.router)
app.include_router(users.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to Contacts API!"}
