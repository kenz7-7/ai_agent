from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, String, Text, Integer, DECIMAL, Enum, Boolean, TIMESTAMP
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.sql import func
from twilio.twiml.voice_response import VoiceResponse
import openai
import os
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

# Retrieve environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
PORT = int(os.getenv("PORT", 5050))

# Print environment variables to ensure they are being loaded
print(f"OPENAI_API_KEY: {OPENAI_API_KEY}")
print(f"DB_HOST: {DB_HOST}")
print(f"DB_PORT: {DB_PORT}")
print(f"DB_USER: {DB_USER}")
print(f"DB_NAME: {DB_NAME}")

SYSTEM_MESSAGE = """You are an AI Receptionist designed to handle customer interactions.
Your responsibilities include: Greeting customers, understanding their queries, providing relevant information, offering demos, facilitating payments, and storing conversations."""

# Validate environment variables
required_env_vars = [
    "OPENAI_API_KEY", "DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD", "DB_NAME"
]
for var in required_env_vars:
    if not os.getenv(var):
        raise ValueError(f"Missing required environment variable: {var}")

# Initialize OpenAI
openai.api_key = OPENAI_API_KEY

# Database setup
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
