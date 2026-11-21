
from database import appointments_collection
from datetime import datetime, timezone
from uuid import uuid4


VALID_FIELDS = {
    "patient_name",
    "age",
    "contact_number",
    "appointment_date",
    "appointment_time",
    "service_name"
}


def book_appointment(form_data):

    required_fields = VALID_FIELDS

    missing_fields = [
        field for field in required_fields
        if form_data.get(field) is None
        or form_data.get(field) == ""
    ]

    if missing_fields:
        return f"Missing required fields: {', '.join(missing_fields)}"

    appointment_id = "APT-" + uuid4().hex[:10].upper()

    appointment = {
        "appointment_id": appointment_id,
        "patient_name": form_data["patient_name"],
        "age": form_data["age"],
        "contact_number": form_data["contact_number"],
        "appointment_date": form_data["appointment_date"],
        "appointment_time": form_data["appointment_time"],
        "service_name": form_data["service_name"],
        "status": "Booked",
        "created_at": datetime.now(timezone.utc)
    }

    appointments_collection.insert_one(appointment)

    return (
        f"Appointment booked successfully for "
        f"{appointment['patient_name']} on "
        f"{appointment['appointment_date']} at "
        f"{appointment['appointment_time']}. "
        f"Your appointment ID is {appointment_id}."
    )


def cancel_appointment(appointment_id):

    result = appointments_collection.update_one(
        {
            "appointment_id": appointment_id,
            "status": "Booked"
        },
        {
            "$set": {
                "status": "Cancelled",
                "cancelled_at": datetime.now(timezone.utc)
            }
        }
    )

    if result.modified_count == 0:
        return "Appointment not found or already cancelled."

    return f"Appointment {appointment_id} has been cancelled successfully."


def update_appointment(appointment_id, updated_details):

    updated_fields = {
        key: value
        for key, value in updated_details.items()
        if key in VALID_FIELDS and value is not None and value != ""
    }

    if not updated_fields:
        return "No valid appointment details were provided for updating."

    result = appointments_collection.update_one(
        {
            "appointment_id": appointment_id,
            "status": "Booked"
        },
        {
            "$set": {
                **updated_fields,
                "updated_at": datetime.now(timezone.utc)
            }
        }
    )

    if result.matched_count == 0:
        return "Appointment not found or is no longer active."

    return f"Appointment {appointment_id} has been updated successfully."


def search_appointment(appointment_id):

    appointment = appointments_collection.find_one(
        {"appointment_id": appointment_id},
        {"_id": 0}
    )

    if appointment is None:
        return "No appointment found with that ID."

    return (
        f"Appointment details: "
        f"Patient: {appointment['patient_name']}, "
        f"Date: {appointment['appointment_date']}, "
        f"Time: {appointment['appointment_time']}, "
        f"Service: {appointment['service_name']}, "
        f"Status: {appointment['status']}."
    )
