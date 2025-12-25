"""
Appointment Service - Enhanced with Phone-based Operations
Supports: Book with doctor/reason, View by phone, Edit by phone, Cancel by phone
"""

from typing import Dict, List, Optional
from datetime import datetime
from services import calendar_service

class AppointmentService:
    """
    Tool layer for appointment operations
    Now supports phone-based view, edit, and cancel
    """
    
    @staticmethod
    async def book_appointment(
        patient_name: str,
        patient_phone: str,
        date: str,
        time: str,
        reason: str = "General consultation",
        doctor_name: Optional[str] = None
    ) -> Dict:
        """
        Book a new appointment
        Now properly handles doctor and reason
        """
        print(f"[*] Booking appointment for {patient_name}")
        
        # Parse date/time
        start_time = calendar_service.parse_datetime(date, time)
        
        if start_time is None:
            return {
                "success": False,
                "message": f"Could not parse date/time: {date} {time}"
            }
        
        # Set defaults
        if not doctor_name:
            doctor_name = "Any available doctor"
        if not reason or reason.strip() == "":
            reason = "General consultation"
        
        # Create appointment
        result = calendar_service.create_appointment(
            patient_name=patient_name,
            patient_phone=patient_phone,
            start_time=start_time,
            reason=reason,
            doctor_name=doctor_name
        )
        
        return result
    
    @staticmethod
    async def view_appointments(phone: str) -> Dict:
        """
        View all appointments for a phone number
        """
        print(f"👀 Viewing appointments for {phone}")
        
        appointments = calendar_service.get_appointments_by_phone(phone)
        
        if not appointments:
            return {
                "success": True,
                "appointments": [],
                "message": "No appointments found for this phone number"
            }
        
        # Sort by date
        appointments.sort(key=lambda x: x['start_time'])
        
        return {
            "success": True,
            "appointments": appointments,
            "message": f"Found {len(appointments)} appointment(s)"
        }
    
    @staticmethod
    async def cancel_appointment_by_phone(phone: str) -> Dict:
        """
        Cancel appointment using phone number
        If multiple appointments exist, cancel the most recent upcoming one
        """
        print(f"[-] Cancelling appointment for {phone}")
        
        appointments = calendar_service.get_appointments_by_phone(phone)
        
        if not appointments:
            return {
                "success": False,
                "message": "No appointments found for this phone number"
            }
        
        # Filter upcoming appointments
        now = datetime.now(calendar_service.pytz.timezone(calendar_service.TIMEZONE))
        upcoming = [
            apt for apt in appointments 
            if datetime.fromisoformat(apt['start_time']) > now
        ]
        
        if not upcoming:
            return {
                "success": False,
                "message": "No upcoming appointments found"
            }
        
        # Sort by date and get the earliest upcoming one
        upcoming.sort(key=lambda x: x['start_time'])
        appointment_to_cancel = upcoming[0]
        
        # Cancel it
        result = calendar_service.cancel_appointment(appointment_to_cancel['id'])
        
        if result['success']:
            return {
                "success": True,
                "message": f"Cancelled appointment on {appointment_to_cancel['start_time']}",
                "cancelled_appointment": appointment_to_cancel
            }
        else:
            return result
    
    @staticmethod
    async def update_appointment_by_phone(
        phone: str,
        new_date: Optional[str] = None,
        new_time: Optional[str] = None,
        new_doctor: Optional[str] = None,
        new_reason: Optional[str] = None
    ) -> Dict:
        """
        Update appointment using phone number
        If multiple appointments exist, update the most recent upcoming one
        Can update: date, time, doctor, reason
        """
        print(f"[*] Updating appointment for {phone}")
        
        appointments = calendar_service.get_appointments_by_phone(phone)
        
        if not appointments:
            return {
                "success": False,
                "message": "No appointments found for this phone number"
            }
        
        # Filter upcoming appointments
        now = datetime.now(calendar_service.pytz.timezone(calendar_service.TIMEZONE))
        upcoming = [
            apt for apt in appointments 
            if datetime.fromisoformat(apt['start_time']) > now
        ]
        
        if not upcoming:
            return {
                "success": False,
                "message": "No upcoming appointments found to modify"
            }
        
        # Sort by date and get the earliest upcoming one
        upcoming.sort(key=lambda x: x['start_time'])
        appointment_to_update = upcoming[0]
        appointment_id = appointment_to_update['id']
        
        # Build updates dict
        updates = {}
        
        # Update date/time if provided
        if new_date and new_time:
            new_start_time = calendar_service.parse_datetime(new_date, new_time)
            if new_start_time is None:
                return {
                    "success": False,
                    "message": f"Could not parse new date/time: {new_date} {new_time}"
                }
            updates['start_time'] = new_start_time
        
        # Update doctor if provided
        if new_doctor:
            updates['doctor_name'] = new_doctor
        
        # Update reason if provided
        if new_reason:
            updates['reason'] = new_reason
        
        if not updates:
            return {
                "success": False,
                "message": "No changes specified. Please provide new date, time, doctor, or reason."
            }
        
        # Perform update
        result = calendar_service.update_appointment(appointment_id, updates)
        
        return result
    
    @staticmethod
    async def get_available_slots(date: str) -> Dict:
        """Get available slots for a date"""
        print(f"🔍 Checking available slots for {date}")
        
        # Parse date
        tz = calendar_service.pytz.timezone(calendar_service.TIMEZONE)
        now = datetime.now(tz)
        
        # Simple date parsing for this helper
        date_lower = date.lower()
        if date_lower == 'today':
            target_date = now
        elif date_lower == 'tomorrow':
            target_date = now + calendar_service.timedelta(days=1)
        else:
            # Try to parse
            parsed_dt = calendar_service.parse_datetime(date, "09:00")
            if parsed_dt is None:
                return {
                    "success": False,
                    "message": f"Could not parse date: {date}"
                }
            target_date = parsed_dt
        
        slots = calendar_service.get_available_slots(target_date)
        
        return {
            "success": True,
            "slots": slots,
            "date": target_date.strftime('%A, %B %d, %Y'),
            "message": f"Found {len(slots)} available slot(s)"
        }

print("[+] Appointment service loaded")