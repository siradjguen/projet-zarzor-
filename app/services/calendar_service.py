
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pytz
from pathlib import Path

TIMEZONE = os.getenv('TIMEZONE', 'Africa/Algiers')  
APPOINTMENTS_FILE = 'appointments.json'

Path('data').mkdir(exist_ok=True)
APPOINTMENTS_PATH = Path('data') / APPOINTMENTS_FILE

def load_appointments() -> List[Dict]:
    """Load appointments from JSON file"""
    try:
        if APPOINTMENTS_PATH.exists():
            with open(APPOINTMENTS_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"✅ Loaded {len(data)} appointments from {APPOINTMENTS_PATH}")
                return data
        print(f"⚠️ No appointments file found at {APPOINTMENTS_PATH}, creating new one")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e}")
        return []
    except Exception as e:
        print(f"❌ Error loading appointments: {e}")
        return []

def save_appointments(appointments: List[Dict]) -> bool:
    """Save appointments to JSON file"""
    try:
        # Ensure directory exists
        APPOINTMENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        with open(APPOINTMENTS_PATH, 'w', encoding='utf-8') as f:
            json.dump(appointments, f, indent=2, default=str, ensure_ascii=False)
        
        print(f"✅ Successfully saved {len(appointments)} appointments to {APPOINTMENTS_PATH}")
        
        # Verify the save worked
        with open(APPOINTMENTS_PATH, 'r', encoding='utf-8') as f:
            verify = json.load(f)
            print(f"✅ Verified: {len(verify)} appointments in file")
        
        return True
    except Exception as e:
        print(f"❌ Error saving appointments: {e}")
        import traceback
        traceback.print_exc()
        return False

def parse_datetime(date_str: str, time_str: str) -> Optional[datetime]:
    """
    Parse date and time strings into datetime object
    
    Examples:
    - "wednesday" + "8am" -> next Wednesday at 8:00 AM
    - "monday" + "2:30pm" -> next Monday at 2:30 PM
    """
    try:
        tz = pytz.timezone(TIMEZONE)
        now = datetime.now(tz)
        
        print(f"🔍 Parsing datetime: date='{date_str}', time='{time_str}'")
        
        # Handle day names
        days = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6,
            'lundi': 0, 'mardi': 1, 'mercredi': 2, 'jeudi': 3,
            'vendredi': 4, 'samedi': 5, 'dimanche': 6
        }
        
        date_lower = date_str.lower().strip()
        
        # If it's a day name
        if date_lower in days:
            target_day = days[date_lower]
            days_ahead = target_day - now.weekday()
            if days_ahead <= 0:  # Target day already happened this week
                days_ahead += 7
            target_date = now + timedelta(days=days_ahead)
        elif date_lower in ['today', "aujourd'hui"]:
            target_date = now
        elif date_lower in ['tomorrow', 'demain']:
            target_date = now + timedelta(days=1)
        else:
            # Try to parse as date string
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d')
                target_date = tz.localize(target_date)
            except:
                print(f"❌ Could not parse date: {date_str}")
                return None
        
        # Parse time - IMPROVED PARSING
        time_lower = time_str.lower().strip().replace(' ', '').replace('.', ':')
        
        # Handle formats: "8am", "8:00am", "14:00", "2:30pm", "8h", "8h30"
        try:
            if 'am' in time_lower or 'pm' in time_lower:
                if ':' in time_lower:
                    time_obj = datetime.strptime(time_lower, '%I:%M%p')
                else:
                    time_obj = datetime.strptime(time_lower, '%I%p')
            elif 'h' in time_lower:  # French format: 8h, 8h30
                time_lower = time_lower.replace('h', ':')
                if ':' not in time_lower:
                    time_lower += ':00'
                time_obj = datetime.strptime(time_lower, '%H:%M')
            else:  # 24h format
                if ':' not in time_lower:
                    time_lower += ':00'
                time_obj = datetime.strptime(time_lower, '%H:%M')
        except Exception as e:
            print(f"❌ Could not parse time '{time_str}': {e}")
            return None
        
        # Combine date and time
        result = target_date.replace(
            hour=time_obj.hour,
            minute=time_obj.minute,
            second=0,
            microsecond=0
        )
        
        print(f"✅ Parsed datetime: {result.strftime('%Y-%m-%d %H:%M %Z')}")
        return result
        
    except Exception as e:
        print(f"❌ Error parsing datetime: {e}")
        import traceback
        traceback.print_exc()
        return None

def check_availability(start_time: datetime, duration: int = 30) -> Dict:
    """
    Check if a time slot is available
    
    Args:
        start_time: Appointment start time
        duration: Duration in minutes (default 30)
        
    Returns:
        Dict with available status and conflicting appointments
    """
    try:
        end_time = start_time + timedelta(minutes=duration)
        
        # Load existing appointments
        appointments = load_appointments()
        
        print(f"🔍 Checking availability for {start_time.strftime('%Y-%m-%d %H:%M')} ({len(appointments)} existing appointments)")
        
        # Check for conflicts
        conflicts = []
        for apt in appointments:
            apt_start = datetime.fromisoformat(apt['start_time'])
            apt_end = datetime.fromisoformat(apt['end_time'])
            
            # Check if there's an overlap
            if (start_time < apt_end) and (end_time > apt_start):
                conflicts.append({
                    'patient_name': apt['patient_name'],
                    'start': apt_start.strftime('%I:%M %p'),
                    'end': apt_end.strftime('%I:%M %p')
                })
        
        if conflicts:
            return {
                "available": False,
                "conflicts": conflicts,
                "message": f"⚠️ Time slot already booked by {conflicts[0]['patient_name']}. Please choose another time."
            }
        
        # Check working hours
        hour = start_time.hour
        weekday = start_time.weekday()
        
        if weekday == 6:  # Sunday
            return {
                "available": False,
                "message": "❌ Nous sommes fermés le dimanche / We are closed on Sundays. Veuillez choisir lundi-samedi / Please choose Monday-Saturday."
            }
        
        if weekday == 5:  # Saturday
            if hour < 9 or hour >= 14:
                return {
                    "available": False,
                    "message": "❌ Horaires samedi: 9h00-14h00 (Heure d'Algérie) / Saturday hours: 9:00 AM-2:00 PM (Algeria Time)"
                }
        else:  # Weekdays
            if hour < 9 or hour >= 18:
                return {
                    "available": False,
                    "message": "❌ Horaires: Lundi-Vendredi 9h00-18h00, Samedi 9h00-14h00 (Heure d'Algérie) / Hours: Mon-Fri 9AM-6PM, Sat 9AM-2PM (Algeria Time)"
                }
        
        # Check if in the past
        tz = pytz.timezone(TIMEZONE)
        now = datetime.now(tz)
        if start_time < now:
            return {
                "available": False,
                "message": "❌ Cannot book appointments in the past. Please choose a future time."
            }
        
        print(f"✅ Time slot is available!")
        return {
            "available": True,
            "message": "✅ Time slot is available!"
        }
        
    except Exception as e:
        print(f"❌ Error checking availability: {e}")
        import traceback
        traceback.print_exc()
        return {
            "available": False,
            "error": str(e),
            "message": "Error checking availability."
        }

def create_appointment(
    patient_name: str,
    patient_phone: str,
    start_time: datetime,
    duration: int = 30,
    reason: str = None,
    doctor_name: str = None
) -> Dict:
    """
    Create an appointment
    
    Args:
        patient_name: Patient's full name
        patient_phone: Patient's phone number
        start_time: Appointment start time
        duration: Duration in minutes (default 30)
        reason: Reason for visit (optional)
        doctor_name: Preferred doctor (optional)
        
    Returns:
        Dict with appointment details or error
    """
    try:
        print(f"\n{'='*60}")
        print(f"📝 CREATING APPOINTMENT")
        print(f"Patient: {patient_name}")
        print(f"Phone: {patient_phone}")
        print(f"Time: {start_time.strftime('%Y-%m-%d %H:%M %Z')}")
        print(f"Duration: {duration} minutes")
        print(f"{'='*60}\n")
        
        # Check availability first
        availability = check_availability(start_time, duration)
        
        if not availability["available"]:
            print(f"❌ Time slot not available: {availability['message']}")
            return {
                "success": False,
                "message": availability["message"],
                "conflicts": availability.get("conflicts")
            }
        
        end_time = start_time + timedelta(minutes=duration)
        
        # Generate unique ID
        import uuid
        appointment_id = str(uuid.uuid4())[:8]
        
        # Create appointment object
        appointment = {
            'id': appointment_id,
            'patient_name': patient_name,
            'patient_phone': patient_phone,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration': duration,
            'reason': reason,
            'doctor_name': doctor_name,
            'created_at': datetime.now(pytz.timezone(TIMEZONE)).isoformat(),
            'status': 'confirmed'
        }
        
        print(f"📋 Appointment object created: {json.dumps(appointment, indent=2, default=str)}")
        
        # Load existing appointments
        appointments = load_appointments()
        print(f"📚 Current appointments count: {len(appointments)}")
        
        # Add new appointment
        appointments.append(appointment)
        print(f"📚 New appointments count: {len(appointments)}")
        
        # Save to file
        if save_appointments(appointments):
            print(f"✅✅✅ APPOINTMENT CREATED SUCCESSFULLY: {appointment_id}")
            print(f"{'='*60}\n")
            
            return {
                "success": True,
                "message": f"✅ Appointment successfully booked for {patient_name}!",
                "appointment_id": appointment_id,
                "start_time": start_time.strftime('%A, %B %d, %Y at %I:%M %p'),
                "end_time": end_time.strftime('%I:%M %p'),
                "duration": duration,
                "details": {
                    "patient_name": patient_name,
                    "patient_phone": patient_phone,
                    "reason": reason,
                    "doctor_name": doctor_name
                }
            }
        else:
            print(f"❌ Failed to save appointment to file")
            return {
                "success": False,
                "message": "Failed to save appointment. Please try again."
            }
        
    except Exception as e:
        print(f"❌ Error creating appointment: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "message": "Failed to create appointment.",
            "error": str(e)
        }

def get_available_slots(date: datetime, duration: int = 30) -> List[str]:
    """
    Get available time slots for a specific date
    
    Args:
        date: The date to check
        duration: Slot duration in minutes
        
    Returns:
        List of available time slots as strings
    """
    try:
        # Determine working hours
        weekday = date.weekday()
        if weekday == 6:  # Sunday
            return []
        elif weekday == 5:  # Saturday
            start_hour, end_hour = 9, 14
        else:  # Weekdays
            start_hour, end_hour = 9, 18
        
        # Generate all possible slots
        all_slots = []
        current = date.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        end = date.replace(hour=end_hour, minute=0, second=0, microsecond=0)
        
        while current < end:
            all_slots.append(current)
            current += timedelta(minutes=duration)
        
        # Check each slot
        available_slots = []
        for slot in all_slots:
            availability = check_availability(slot, duration)
            if availability["available"]:
                available_slots.append(slot.strftime('%I:%M %p'))
        
        return available_slots
        
    except Exception as e:
        print(f"❌ Error getting available slots: {e}")
        return []

def get_appointments_by_phone(phone: str) -> List[Dict]:
    """Get all appointments for a phone number"""
    try:
        appointments = load_appointments()
        return [apt for apt in appointments if apt['patient_phone'] == phone]
    except Exception as e:
        print(f"❌ Error getting appointments: {e}")
        return []

def cancel_appointment(appointment_id: str) -> Dict:
    """
    Cancel an appointment
    
    Args:
        appointment_id: Appointment ID
        
    Returns:
        Dict with cancellation status
    """
    try:
        appointments = load_appointments()
        
        # Find and remove appointment
        original_count = len(appointments)
        appointments = [apt for apt in appointments if apt['id'] != appointment_id]
        
        if len(appointments) < original_count:
            if save_appointments(appointments):
                print(f"✅ Appointment cancelled: {appointment_id}")
                return {
                    "success": True,
                    "message": "✅ Appointment successfully cancelled."
                }
        
        return {
            "success": False,
            "message": "❌ Appointment not found. Please check the ID."
        }
        
    except Exception as e:
        print(f"❌ Error cancelling appointment: {e}")
        return {
            "success": False,
            "message": "Failed to cancel appointment.",
            "error": str(e)
        }

def get_all_appointments() -> List[Dict]:
    """Get all appointments (for admin/testing)"""
    return load_appointments()

def clear_old_appointments():
    """Remove appointments older than today"""
    try:
        appointments = load_appointments()
        tz = pytz.timezone(TIMEZONE)
        now = datetime.now(tz)
        
        # Keep only future appointments
        future_appointments = [
            apt for apt in appointments
            if datetime.fromisoformat(apt['start_time']) > now
        ]
        
        save_appointments(future_appointments)
        print(f"✅ Cleaned up old appointments")
    except Exception as e:
        print(f"❌ Error cleaning appointments: {e}")