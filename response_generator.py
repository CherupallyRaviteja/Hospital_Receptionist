import dotenv
import groq
import json
import os

dotenv.load_dotenv()

groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    raise ValueError("GROQ_API_KEY is missing from .env")

client = groq.Groq(api_key=groq_api_key)

MODEL = "openai/gpt-oss-120b"

from pydantic import BaseModel
from typing import Any

class ReceptionistResponse(BaseModel):
    memory: dict[str, Any]
    is_complete: bool
    response: str


SCHEMA = {
    "patient_name": {
        "label": "Patient Full Name",
        "type": "string",
        "description": "Full name of the patient"
    },
    "age": {
        "label": "Patient Age",
        "type": "integer",
        "description": "Age of the patient"
    },
    "contact_number": {
        "label": "Contact Number",
        "type": "string",
        "description": "Patient's mobile number"
    },
    "appointment_date": {
        "label": "Appointment Date",
        "type": "string",
        "description": "Preferred appointment date"
    },
    "appointment_time": {
        "label": "Appointment Time",
        "type": "string",
        "description": "Preferred appointment time"
    },
    "service_name": {
        "label": "Medical Service",
        "type": "string",
        "description": "Requested medical department or specialty"
    }
}

REQUIRED_FIELDS = [
    "patient_name",
    "age",
    "contact_number",
    "appointment_date",
    "appointment_time",
    "service_name"
]

memory = json.load(open("content_memory.json"))


SYSTEM_PROMPT = """
You are an AI hospital receptionist responsible for collecting patient information and managing appointment-related requests.

YOUR RESPONSIBILITIES:

1. Collect all information required to perform the requested service.
2. Maintain conversation memory and update it whenever the user provides new information.
3. Never ask the user for information that has already been collected.
4. If the user corrects previously provided information, update the stored value.
5. Ask only for the missing required fields.
6. Do not invent or assume patient information.

INPUT CONTEXT:

Required Fields:
{required_fields}

Current Memory:
{memory}

CURRENT USER MESSAGE:
{user_message}

INSTRUCTIONS:

1. Extract relevant information from the user's message.
2. Compare the extracted information with the required fields.
3. Update memory with newly provided or corrected information.
4. Check memory to verify whether all required fields have been collected.
5. If fields are missing, ask the user a natural, concise question to collect the missing information.
6. If all required fields are collected, indicate that the information collection is complete.

OUTPUT RULES:

Return a JSON object with exactly these fields:

{{
    "memory": {{
        "field_name": "collected_value"
    }},
    "is_complete": true,
    "response": "Message to the user"
}}

RULES:

- Use null for fields that have not been collected.
- Preserve the correct data types.
- Set is_complete to true only when all required fieldshave valid values.
- Set is_complete to true only when all required fields are collected.
- Otherwise, set is_complete to false.
- Preserve previously collected information.
- Never overwrite valid information unless the user corrects it.
- Return valid JSON only.
"""

messages = [
    {
        "role": "system",
        "content": SYSTEM_PROMPT
    }
]


import json


def generate_response(message, memory, required_fields):

    system_prompt = SYSTEM_PROMPT.format(
        schema=json.dumps(SCHEMA, indent=4),
        required_fields=json.dumps(required_fields, indent=4),
        memory=json.dumps(memory, indent=4),
        user_message=message
    )

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                }
            ],
            temperature=0.2,
            max_tokens=700,
            response_format={"type": "json_object"}
        )

        answer = response.choices[0].message.content

        # Validate the returned JSON structure
        result = ReceptionistResponse.model_validate_json(answer)

        return result.model_dump()

    except Exception as e:
        print("Groq API Error:", repr(e))
        return None


if __name__ == "__main__":

    with open("content_memory.json", "r") as file:
        memory = json.load(file)

    user_input = "I want to book an appointment."

    result = generate_response(
        message=user_input,
        memory=memory,
        required_fields=REQUIRED_FIELDS
    )

    if result:

        memory.update(result["memory"])

        with open("content_memory.json", "w") as file:
            json.dump(memory, file, indent=4)

        print("Memory:", memory)
        print("Complete:", result["is_complete"])
        print("Receptionist:", result["response"])