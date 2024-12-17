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
Base = declarative_base()


# Define Customer model
class Customer(Base):
    __tablename__ = "customers"
    customer_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email_id = Column(String(150), unique=True, nullable=False)
    phone_number = Column(String(15), nullable=False)
    demo = Column(Boolean, nullable=False, default=True)
    service = Column(String(100))
    payment_status = Column(Enum("Pending", "Completed"), default="Pending")
    pending_balance = Column(DECIMAL(10, 2), default=0.00)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)


# Define Conversation model
class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), nullable=False)
    transcript = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)


Base.metadata.create_all(bind=engine)

# Initialize FastAPI
app = FastAPI()

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Root Route
@app.get("/")
async def root():
    return {"message": "AI Receptionist Server is running!"}


# Incoming Call Route (Twilio Webhook)
@app.post("/incoming-call")
async def incoming_call(request: Request):
    """Twilio webhook for handling calls."""
    response = VoiceResponse()
    response.say("Hi, you have called Kenvoice. How can we help?")
    # curl -X POST http://0.0.0.0:5050/incoming-call

    # Use WebSocket URL for media streaming (replace with actual URL)
    replit_url = "wss://https://45ff893a-f523-454f-9995-9980cd12c41d-00-3qz3u5gkpx8h2.pike.replit.dev/.replit.app"  # Replace with your actual Replit URL

    # Connect Twilio to the WebSocket for media streaming
    response.connect().stream(url=f"{replit_url}/media-stream")

    return JSONResponse(content=str(response), media_type="application/xml")


# WebSocket for Media Stream
@app.websocket("/media-stream")
async def media_stream(websocket: WebSocket):
    """Handle WebSocket for streaming data."""
    await websocket.accept()

    # Ensure session id is passed for tracking
    session_id = websocket.headers.get("x-twilio-call-sid",
                                       f"session_{int(time.time())}")

    db_session = SessionLocal()
    conversation = db_session.query(Conversation).filter_by(
        session_id=session_id).first()

    # If no conversation exists, create a new one
    if not conversation:
        conversation = Conversation(session_id=session_id, transcript="")
        db_session.add(conversation)
        db_session.commit()

    try:
        while True:
            # Receive data (audio or text) from WebSocket
            data = await websocket.receive_text(
            )  # Change to receive binary data if you are dealing with audio

            # Call OpenAI to process the text data
            try:
                response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[
                        {
                            "role": "system",
                            "content": SYSTEM_MESSAGE
                        },
                        {
                            "role": "user",
                            "content": data
                        },
                    ],
                )

                # If response from OpenAI is successful, reply with the AI's message
                if "choices" in response:
                    reply = response["choices"][0]["message"]["content"]
                    conversation.transcript += f"\nUser: {data}\nAI: {reply}"
                    db_session.commit()
                    await websocket.send_text(reply)
                else:
                    print("No choices in OpenAI response.")
                    await websocket.send_text(
                        "Sorry, I couldn't understand that.")
            except Exception as e:
                print(f"Error in OpenAI API call: {e}")
                await websocket.send_text(
                    "Sorry, something went wrong. Please try again.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db_session.close()
        await websocket.close()


# Shutdown Event
@app.on_event("shutdown")
def shutdown_event():
    engine.dispose()


# Run the app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
