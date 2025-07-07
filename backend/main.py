from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from backend.google_calendar import get_free_slots, book_slot
from backend.agent import run_agent

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class BookingRequest(BaseModel):
    date: str  # YYYY-MM-DD
    start_time: str  # HH:MM (24h)
    end_time: str    # HH:MM (24h)
    title: str = "Appointment"
    description: str = "Booked via Assistant"

class AgentQuery(BaseModel):
    prompt: str

@app.get("/availability")
def check_availability(date: str):
    slots = get_free_slots(date)
    return {"busy": slots}

@app.post("/book")
def create_booking(data: BookingRequest):
    from datetime import datetime
    start = f"{data.date}T{data.start_time}:00+05:30"
    end = f"{data.date}T{data.end_time}:00+05:30"
    link = book_slot(start, end, data.title, data.description)
    return {"message": "Booking confirmed!", "event_link": link}

@app.post("/agent")
def handle_agent(query: AgentQuery):
    response = run_agent(query.prompt)
    return {"response": response}