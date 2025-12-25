"""
Calendar Service - FIXED: Privacy-Safe Conflict Messages
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pytz

from app.config import APPOINTMENTS_FILE, TIMEZONE, CLINIC_CONFIG

def load_appointments() -> List[Dict]:
    """Load all appointments from JSON file"""
    try:
        if APPOINTMENTS_FILE.exists():
            with open(APPOINTMENTS_FILE, 'r', encoding='utf-8') as f:
                appointments = json.load(f)
                print(f"📋 Loaded {len(appointments)} appointments")
                return appointments
        print("📋 No appointments file found, starting fresh")
        return []
    except Exception as e:
        print(f"❌ Error loading appointments: {e}")
        return []

def save_appointments(appointments: List[Dict]) -> bool:
    """Save appointments to JSON file"""
    try:
        with open(APPOINTMENTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(appointments, f, indent=2, default=str, ensure_ascii=False)
        print(f"💾 Saved {len(appointments)} appointments")
        return True
    except Exception as e:
        print(f"❌ Error saving appointments: {e}")
        return False

def parse_datetime(date_str: str, time_str: str) -> Optional[datetime]:
    """Parse human-readable date/time into datetime object"""
    try:
        tz = pytz.timezone(TIMEZONE)
        now = datetime.now(tz)
        
        # Month name mappings
        month_names = {
            'january': 1, 'jan': 1, 'januray': 1, 'janury': 1,
            'february': 2, 'feb': 2, 'febuary': 2, 'feburary': 2,
            'march': 3, 'mar': 3,
            'april': 4, 'apr': 4, 'apirl': 4,
            'may': 5,
            'june': 6, 'jun': 6,
            'july': 7, 'jul': 7,
            'august': 8, 'aug': 8,
            'september': 9, 'sep': 9, 'sept': 9,
            'october': 10, 'oct': 10, 'ocotber': 10, 'otober': 10,
            'november': 11, 'nov': 11, 'novmber': 11,
            'december': 12, 'dec': 12, 'decemeber': 12, 'decembre': 12, 'decmber': 12, 'decembe': 12
        }
        
        # Day name mappings
        days = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6,
            'lundi': 0, 'mardi': 1, 'mercredi': 2, 'jeudi': 3,
            'vendredi': 4, 'samedi': 5, 'dimanche': 6
        }
        
        date_lower = date_str.lower().strip()
        target_date = None
        
        # Handle typos for "tomorrow"
        if date_lower in ['tomorow', 'tommorow', 'tommorrow']:
            date_lower = 'tomorrow'
        
        # Relative dates
        if date_lower in ['today', "aujourd'hui"]:
            target_date = now
        elif date_lower in ['tomorrow', 'demain']:
            target_date = now + timedelta(days=1)
        elif date_lower in ['yesterday', 'hier']:
            target_date = now - timedelta(days=1)
        elif date_lower in days:
            target_day = days[date_lower]
            days_ahead = target_day - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            target_date = now + timedelta(days=days_ahead)
        else:
            parsed = False
            parts = date_lower.split()
            day = None
            month = None
            year = now.year
            
            for part in parts:
                if part.isdigit():
                    num = int(part)
                    if num <= 31:
                        day = num
                    elif num > 1000:
                        year = num
                elif part in month_names:
                    month = month_names[part]
            
            if day and month:
                try:
                    target_date = datetime(year, month, day)
                    target_date = tz.localize(target_date)
                    parsed = True
                    print(f"[✓] Parsed date: {date_str} -> {target_date.strftime('%Y-%m-%d')}")
                except ValueError as e:
                    print(f"❌ Invalid date values: day={day}, month={month}, year={year}")
                    return None
            
            if not parsed:
                try:
                    target_date = datetime.strptime(date_str, '%Y-%m-%d')
                    target_date = tz.localize(target_date)
                    parsed = True
                except:
                    pass
            
            if not parsed:
                for fmt in ['%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y']:
                    try:
                        target_date = datetime.strptime(date_str, fmt)
                        target_date = tz.localize(target_date)
                        parsed = True
                        break
                    except:
                        continue
            
            if not parsed:
                print(f"❌ Could not parse date: {date_str}")
                return None
        
        # Parse time
        time_lower = time_str.lower().strip().replace(' ', '').replace('.', ':')
        time_clean = time_lower
        time_obj = None
        
        if 'am' in time_clean or 'pm' in time_clean:
            if ':' in time_clean:
                time_obj = datetime.strptime(time_clean, '%I:%M%p')
            else:
                time_obj = datetime.strptime(time_clean, '%I%p')
        elif 'h' in time_clean:
            time_clean = time_clean.replace('h', ':')
            if ':' not in time_clean:
                time_clean += ':00'
            time_obj = datetime.strptime(time_clean, '%H:%M')
        elif ':' in time_clean:
            time_obj = datetime.strptime(time_clean, '%H:%M')
        else:
            try:
                hour = int(time_clean)
                if hour == 12:
                    pass
                elif 1 <= hour <= 6:
                    hour += 12
                elif 7 <= hour <= 11:
                    pass
                elif 13 <= hour <= 23:
                    pass
                else:
                    print(f"❌ Invalid hour: {hour}")
                    return None
                time_obj = datetime.strptime(f"{hour}:00", '%H:%M')
            except ValueError:
                print(f"❌ Could not parse time: {time_str}")
                return None
        
        if time_obj is None:
            print(f"❌ Could not parse time: {time_str}")
            return None
        
        result = target_date.replace(
            hour=time_obj.hour,
            minute=time_obj.minute,
            second=0,
            microsecond=0
        )
        
        day_name = result.strftime('%A')
        formatted = result.strftime('%B %d at %I:%M %p')
        print(f"[+] Parsed: {date_str} {time_str} -> {day_name}, {formatted}")
        
        return result
        
    except Exception as e:
        print(f"[-] Error parsing datetime '{date_str}' '{time_str}': {e}")
        import traceback
        traceback.print_exc()
        return None

def check_availability(start_time: datetime, duration: int = None, exclude_appointment_id: str = None) -> Dict:
    """
    Check if time slot is available
    FIXED: Privacy-safe conflict messages - doesn't expose patient names
    """
    if duration is None:
        duration = CLINIC_CONFIG["appointment_duration"]
    
    end_time = start_time + timedelta(minutes=duration)
    
    # Check conflicts (excluding the appointment being updated)
    appointments = load_appointments()
    for apt in appointments:
        # Skip the appointment being updated
        if exclude_appointment_id and apt['id'] == exclude_appointment_id:
            print(f"[*] Skipping conflict check for appointment being updated: {exclude_appointment_id}")
            continue
            
        apt_start = datetime.fromisoformat(apt['start_time'])
        apt_end = datetime.fromisoformat(apt['end_time'])
        
        if (start_time < apt_end) and (end_time > apt_start):
            # FIXED: Don't expose patient name in conflict message
            return {
                "available": False,
                "message": f"Time slot is already booked",
                "reason": "conflict",
                "conflicting_appointment_id": apt['id'],  # Keep ID for internal use only
                "conflicting_time": apt_start.strftime('%I:%M %p')
            }
    
    # Check working hours
    day_name = start_time.strftime('%A').lower()
    hours = CLINIC_CONFIG["working_hours"].get(day_name)
    
    if hours is None:
        return {
            "available": False,
            "message": f"Clinic closed on {day_name.title()}",
            "reason": "closed"
        }
    
    hour = start_time.hour
    if hour < hours["start"] or hour >= hours["end"]:
        return {
            "available": False,
            "message": f"Outside working hours ({hours['start']}:00-{hours['end']}:00)",
            "reason": "outside_hours"
        }
    
    # Check if in past
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    if start_time < now:
        return {
            "available": False,
            "message": "Cannot book in the past",
            "reason": "past"
        }
    
    return {
        "available": True,
        "message": "Available"
    }

def create_appointment(
    patient_name: str,
    patient_phone: str,
    start_time: datetime,
    duration: int = None,
    reason: str = "Consultation",
    doctor_name: str = None
) -> Dict:
    """Create new appointment"""
    if duration is None:
        duration = CLINIC_CONFIG["appointment_duration"]
    
    # Check availability
    availability = check_availability(start_time, duration)
    if not availability["available"]:
        return {
            "success": False,
            "message": availability["message"],
            "reason": availability["reason"],
            "conflicting_time": availability.get("conflicting_time")
        }
    
    # Create appointment
    end_time = start_time + timedelta(minutes=duration)
    appointment_id = str(uuid.uuid4())[:8]
    
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
    
    # Save
    appointments = load_appointments()
    appointments.append(appointment)
    
    if save_appointments(appointments):
        print(f"[+] Appointment created: {appointment_id}")
        return {
            "success": True,
            "message": "Appointment booked successfully",
            "appointment_id": appointment_id,
            "appointment": appointment
        }
    else:
        return {
            "success": False,
            "message": "Failed to save appointment"
        }

def cancel_appointment(appointment_id: str) -> Dict:
    """Cancel appointment by ID"""
    appointments = load_appointments()
    original_count = len(appointments)
    
    appointments = [apt for apt in appointments if apt['id'] != appointment_id]
    
    if len(appointments) < original_count:
        if save_appointments(appointments):
            print(f"[+] Cancelled appointment: {appointment_id}")
            return {
                "success": True,
                "message": "Appointment cancelled"
            }
    
    return {
        "success": False,
        "message": "Appointment not found"
    }

def update_appointment(appointment_id: str, updates: Dict) -> Dict:
    """
    Update appointment by ID
    FIXED: Privacy-safe conflict messages
    """
    appointments = load_appointments()
    
    apt_index = None
    for i, apt in enumerate(appointments):
        if apt['id'] == appointment_id:
            apt_index = i
            break
    
    if apt_index is None:
        return {
            "success": False,
            "message": "Appointment not found"
        }
    
    apt = appointments[apt_index]
    
    # If updating start_time, check availability (excluding this appointment)
    if 'start_time' in updates:
        new_dt = updates['start_time']
        if isinstance(new_dt, datetime):
            duration = apt.get('duration', 30)
            
            # Pass the appointment ID to exclude it from conflict check
            availability = check_availability(new_dt, duration, exclude_appointment_id=appointment_id)
            
            if not availability["available"]:
                print(f"❌ Cannot update: {availability['message']}")
                return {
                    "success": False,
                    "message": availability["message"],
                    "reason": availability.get("reason"),
                    "conflicting_time": availability.get("conflicting_time")
                }
            
            # Update the time
            apt['start_time'] = new_dt.isoformat()
            end_dt = new_dt + timedelta(minutes=duration)
            apt['end_time'] = end_dt.isoformat()
            print(f"[+] Updated time to: {new_dt.strftime('%Y-%m-%d %H:%M')}")
    
    if 'doctor_name' in updates:
        apt['doctor_name'] = updates['doctor_name']
        print(f"[+] Updated doctor to: {updates['doctor_name']}")
    
    if 'reason' in updates:
        apt['reason'] = updates['reason']
        print(f"[+] Updated reason to: {updates['reason']}")
    
    if save_appointments(appointments):
        print(f"[+] Updated appointment: {appointment_id}")
        return {
            "success": True,
            "message": "Appointment updated successfully",
            "appointment": apt
        }
    else:
        return {
            "success": False,
            "message": "Failed to save appointment"
        }

def get_appointments_by_phone(phone: str) -> List[Dict]:
    """Get all appointments for a phone number"""
    appointments = load_appointments()
    return [apt for apt in appointments if apt['patient_phone'] == phone]

def get_all_appointments() -> List[Dict]:
    """Get all appointments"""
    return load_appointments()

def get_available_slots(date: datetime, duration: int = None) -> List[str]:
    """Get available time slots for a date"""
    if duration is None:
        duration = CLINIC_CONFIG["appointment_duration"]
    
    day_name = date.strftime('%A').lower()
    hours = CLINIC_CONFIG["working_hours"].get(day_name)
    
    if hours is None:
        return []
    
    slots = []
    current = date.replace(hour=hours["start"], minute=0, second=0, microsecond=0)
    end = date.replace(hour=hours["end"], minute=0, second=0, microsecond=0)
    
    while current < end:
        availability = check_availability(current, duration)
        if availability["available"]:
            slots.append(current.strftime('%I:%M %p'))
        current += timedelta(minutes=duration)
    
    return slots

def get_today_appointments() -> List[Dict]:
    """Get today's appointments"""
    tz = pytz.timezone(TIMEZONE)
    today = datetime.now(tz).date()
    
    appointments = load_appointments()
    today_apts = []
    
    for apt in appointments:
        apt_date = datetime.fromisoformat(apt['start_time']).date()
        if apt_date == today:
            today_apts.append(apt)
    
    return sorted(today_apts, key=lambda x: x['start_time'])

print("[+] Calendar service loaded (FIXED: Privacy-Safe Messages)")