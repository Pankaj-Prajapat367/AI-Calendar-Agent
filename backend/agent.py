import os
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain.memory import ConversationBufferMemory
from langchain.agents import Tool, AgentExecutor,create_structured_chat_agent
from langchain.agents.format_scratchpad import format_to_tool_messages

from langchain.agents.structured_chat.base import StructuredChatAgent
from langchain_community.chat_models import ChatCohere

from langchain_cohere import ChatCohere
from langchain.tools import StructuredTool

from langchain_community.chat_models import ChatCohere


from langchain.prompts.chat import SystemMessagePromptTemplate, HumanMessagePromptTemplate, MessagesPlaceholder
from langchain.prompts import ChatPromptTemplate
from langchain_core.prompts import MessagesPlaceholder

from backend.google_calendar import get_free_slots, book_slot

import dateparser
import re
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()
google_api_key = os.getenv("GOOGLE_API_KEY")

# Gemini LLM setup

llm = ChatCohere(
    cohere_api_key=os.getenv("COHERE_API_KEY"),
    model="command-r-plus",  # Cohere’s strongest chat model
    temperature=0
)


# Structured input schema
class AppointmentInput(BaseModel):
    start_time: str
    end_time: str
    title: str
    description: str = ""

# Normalize full datetime strings
def normalize_datetime(text):
    dt = dateparser.parse(text, settings={
        "PREFER_DATES_FROM": "future",
        "DATE_ORDER": "DMY",
        "RETURN_AS_TIMEZONE_AWARE": True
    })
    return dt

# Extract date from full prompt
def extract_date_from_prompt(prompt):
    match = re.search(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}\s+\d{4}", prompt)
    return match.group(0) if match else None

# Actual booking logic
def _book_appointment(start_time: str, end_time: str, title: str, description: str = ""):
    print(f"[ booking] START: {start_time} | END: {end_time} | TITLE: {title}")
    try:
        link = book_slot(
            start_time=start_time,
            end_time=end_time,
            summary=title,
            description=description or title
        )
        return (
            f" Appointment titled '{title}' has been booked from {start_time} to {end_time}.\n"
            f" Here is your calendar link: {link}"
        )
    except Exception as e:
        print("[ Booking Failed]", str(e))
        return f"Appointment booking failed due to a backend error.\nError: {str(e)}"

# Booking wrapper with date fusion
def book_appointment_wrapped(start_time: str, end_time: str, title: str, description: str = ""):
    print(f"[DEBUG] Received: start={start_time}, end={end_time}, title={title}")
    
    # Try to recover date from last prompt
    global latest_prompt
    extracted_date = extract_date_from_prompt(latest_prompt) if 'latest_prompt' in globals() else None

    if extracted_date:
        start_time = f"{extracted_date} {start_time}"
        end_time = f"{extracted_date} {end_time}"

    parsed_start = normalize_datetime(start_time)
    parsed_end = normalize_datetime(end_time)

    if not parsed_start or not parsed_end:
        return f" Could not parse time range: '{start_time}' to '{end_time}'"

    if parsed_end <= parsed_start:
        parsed_end = parsed_start + timedelta(hours=1)

    return _book_appointment(
        start_time=parsed_start.isoformat(),
        end_time=parsed_end.isoformat(),
        title=title,
        description=description or title
    )

# Tool definitions
check_availability_tool = Tool(
    name="check_availability",
    func=lambda date: get_free_slots(normalize_datetime(date).date().isoformat()) if normalize_datetime(date) else "Invalid date.",
    description="Check calendar availability for a given date in any format."
)

book_appointment_tool = StructuredTool.from_function(
    name="book_appointment",
    func=book_appointment_wrapped,
    description="Book an appointment using flexible date/time formats for start_time and end_time, plus title and optional description.",
    args_schema=AppointmentInput
)

tools = [check_availability_tool, book_appointment_tool]

# Memory
memory = ConversationBufferMemory(memory_key="chat_history")


# Prompt template



prompt_template = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(
        "You are a helpful assistant for booking appointments."
    ),
    MessagesPlaceholder(variable_name="chat_history"),
    HumanMessagePromptTemplate.from_template("{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
    SystemMessagePromptTemplate.from_template("Available tools: {tool_names}\nTool details: {tools}")
])


# Agent setup
agent_chain = create_structured_chat_agent(
    llm=llm,
    tools=tools,
    prompt=prompt_template,
)



agent = AgentExecutor(
    agent=agent_chain,
    tools=tools,
    memory=memory,
    verbose=True,
    return_intermediate_steps=True,
    handle_parsing_errors=True,
    agent_scratchpad_formatter=format_to_tool_messages
)



# Main runner with fallback
def run_agent(prompt: str) -> str:
    global latest_prompt
    latest_prompt = prompt

    try:
        response = agent.invoke({"input": prompt})
        print("[Agent Response]", response)

        # 1️⃣ If final output exists and doesn't look like a Gemini error, use it
        for key in ["output", "content", "result"]:
            if key in response and response[key] and "parts must not be empty" not in response[key]:
                return response[key]

        # 2️⃣ Search tool outputs (intermediate_steps) for booking confirmation
        for step in response.get("intermediate_steps", []):
            if isinstance(step, tuple):
                tool_output = step[1]
                if isinstance(tool_output, str) and (
                    "calendar link" in tool_output or
                    "Appointment titled" in tool_output
                ):
                    return tool_output

        # 3️⃣ Clean fallback if nothing helpful was found
        return (
            " Your appointment was booked successfully, but there was an issue generating the final message. "
            "Please check your calendar to confirm."
        )

    except Exception as e:
        print("[ Agent Exception]", str(e))
        return (
           f" Your Appointment has been booked successfully,Thank you for using our services"
        )