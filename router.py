from pydantic import BaseModel
from typing import Literal
from google import genai
import dotenv
import os

# Load environment variables
dotenv.load_dotenv()

gemini_api_key = os.getenv("GEMINI_API_KEY")

if not gemini_api_key:
    raise ValueError("GEMINI_API_KEY is missing from .env")

# Initialize Gemini client with timeout
client = genai.Client(
    api_key=gemini_api_key,
    http_options={
        "timeout": 15000,
        "api_version": "v1beta"
    }
)


# Classification response schema
class ServiceClassification(BaseModel):
    service_type: Literal[
        "Book_Appointment",
        "Cancel_Appointment",
        "Update_Appointment",
        "Search_Appointment",
        "Other"
    ]


SYSTEM_PROMPT = """
You are an intent classification system for a doctor appointment service.

1. Book_Appointment:
   User wants to schedule a new doctor appointment.

2. Cancel_Appointment:
   User wants to cancel an existing appointment.

3. Update_Appointment:
   User wants to change an existing appointment.

4. Search_Appointment:
   User wants to check or retrieve an existing appointment.

5. Other:
   Any request unrelated to the above services.

Rules:
- Identify the user's primary intent.
- Do not assume an intent if it is unclear.
- Return only the classification.
"""


# Required fields for each service
SERVICE_FIELDS = {
    "Book_Appointment": {
        "patient_name": "",
        "age": "",
        "contact_number": "",
        "appointment_date": "",
        "appointment_time": "",
        "service_name": ""
    },

    "Cancel_Appointment": {
        "appointment_id": ""
    },

    "Update_Appointment": {
        "appointment_id": "",
        "updated_details": {}
    },

    "Search_Appointment": {
        "appointment_id": ""
    },

    "Other": {}
}


def classify_service_type(message):

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"{SYSTEM_PROMPT}\n\nUser message: {message}",
            config={
                "response_mime_type": "application/json",
                "response_schema": ServiceClassification
            }
        )

        result = ServiceClassification.model_validate_json(
            response.text
        )

        service_type = result.service_type

        required_fields = SERVICE_FIELDS[service_type].copy()

        return service_type, required_fields

    except Exception as e:
        print("Classification error:", repr(e))
        return "Other", {}


if __name__ == "__main__":

    message = "I want to book an appointment tomorrow."

    print("Classifying user intent...")

    service_type, required_fields = classify_service_type(message)

    print("Service Type:", service_type)
    print("Required Fields:", required_fields)
