
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
DATABASE_NAME = os.getenv("MONGODB_DATABASE", "hospital_db")

if not MONGODB_URI:
    raise ValueError("MONGODB_URI is missing from .env")

client = MongoClient(
    MONGODB_URI,
    serverSelectionTimeoutMS=5000
)

# Verify connection
client.admin.command("ping")

db = client[DATABASE_NAME]
appointments_collection = db["appointments"]

# Prevent duplicate appointment IDs
appointments_collection.create_index(
    "appointment_id",
    unique=True
)

print("MongoDB connected successfully.")
