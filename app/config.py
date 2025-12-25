"""
Configuration file for MediBook Clinic
Centralized settings for the entire application
"""

import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Data directory
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Appointments storage
APPOINTMENTS_FILE = DATA_DIR / "appointments.json"

# Timezone
TIMEZONE = "Africa/Algiers"

# Clinic Configuration
CLINIC_CONFIG = {
    "name": "MediBook Clinic",
    "appointment_duration": 30,  # minutes
    "working_hours": {
        "monday": {"start": 9, "end": 18},
        "tuesday": {"start": 9, "end": 18},
        "wednesday": {"start": 9, "end": 18},
        "thursday": {"start": 9, "end": 18},
        "friday": {"start": 9, "end": 18},
        "saturday": {"start": 9, "end": 14},
        "sunday": None  # Closed
    }
}

# LLM Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"  # Model-agnostic architecture

# Session Configuration
SESSION_TIMEOUT = 3600  # 1 hour in seconds

print("[+] Configuration loaded")
print("[*] Data directory:", DATA_DIR)
print("[*] Clinic:", CLINIC_CONFIG['name'])
print("[*] LLM Model:", GROQ_MODEL)