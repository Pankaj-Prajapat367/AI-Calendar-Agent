from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import pytz

load_dotenv()  # Loads variables from .env into environment

SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE =  "/etc/secrets/service_account.json"

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)

calendar_id = os.getenv("CALENDAR_ID")  # Set in .env or hardcoded for testing
print("[ENV DEBUG]", SERVICE_ACCOUNT_FILE, calendar_id)
service = build('calendar', 'v3', credentials=credentials)

def get_free_slots(date_str):
    tz = pytz.timezone("Asia/Kolkata")
    date = datetime.strptime(date_str, "%Y-%m-%d")
    start_time = tz.localize(datetime.combine(date, datetime.min.time()))
    end_time = tz.localize(datetime.combine(date, datetime.max.time()))

    events = service.events().list(
        calendarId=calendar_id,
        timeMin=start_time.isoformat(),
        timeMax=end_time.isoformat(),
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    busy_slots = [(e['start']['dateTime'], e['end']['dateTime']) for e in events.get('items', [])]
    return busy_slots
    
def book_slot(start_time, end_time, summary="Appointment", description="Booked via assistant"):
    event = {
        'summary': summary,
        'description': description,
        'start': {'dateTime': start_time, 'timeZone': 'Asia/Kolkata'},
        'end': {'dateTime': end_time, 'timeZone': 'Asia/Kolkata'}
    }
    try:
        created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
        print("[Booking succeeded]", created_event)
        return created_event.get('htmlLink')
    except Exception as e:
        print("Booking failed:", str(e))
        raise e
