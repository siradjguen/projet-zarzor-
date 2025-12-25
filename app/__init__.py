"""
MediBook Clinic Application Package
"""

# Load environment variables at package initialization
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / '.env')