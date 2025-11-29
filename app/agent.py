# app/agent.py - FIXED VERSION with Better Name/Time Extraction

import time
import re
from typing import List, Dict, Optional
from groq import Groq
from app.config import GROQ_API_KEY, GROQ_MODEL, MODEL_CONFIG
from app.services.calendar_service import (
    check_availability, 
    create_appointment, 
    get_available_slots,
    parse_datetime,
    get_appointments_by_phone,
    cancel_appointment,
    get_all_appointments
)

# Initialize Groq client
client = Groq(api_key=GROQ_API_KEY)

# System prompt for Algeria medical assistant
SYSTEM_PROMPT = """ROLE: You are a medical customer-service agent. Provide clear, helpful, and polite responses, similar to professional support teams from companies like AliExpress or Amazon.

TONE & STYLE:
* Polite, concise, warm, and professional
* Direct and structured
* No unnecessary details
* No long paragraphs
* Always helpful and solution-oriented
* Use short sentences, but not "too short"

MAIN FUNCTIONS: You assist with:
* Booking medical appointments
* Modifying existing appointments
* Canceling appointments
* Checking appointment status
* Answering simple questions about schedules, doctors, and services

CLINIC INFORMATION:
📍 Location: Alger, Algérie
🕒 Hours: Monday-Friday 9:00-18:00 | Saturday 9:00-14:00 | Sunday: Closed
💰 Fees: Consultation 5,000 DA | Specialist 10,000 DA

INTERACTION RULES:
1. Ask only the necessary information, step by step.
2. Confirm every action clearly.
3. If something is unclear, ask politely for clarification.
4. Always give the next step.
5. Keep responses positive and service-focused.

BOOKING PROCESS:
Collect information in this order:
1. Full name
2. Phone number
3. Preferred date (e.g., Monday, Tuesday, Wednesday)
4. Preferred time (e.g., 9am, 14h30, 2pm)
5. Reason for visit (optional)

When all information is collected and the time slot is available, confirm briefly and add the structured format.

CANCELLATION PROCESS:
1. Ask for phone number
2. Show their appointment(s)
3. Confirm cancellation

LANGUAGE SUPPORT:
Respond naturally in the language the user uses (English, French, or Arabic).

EXAMPLES OF YOUR RESPONSE STYLE:
* "Sure, I can help you with that. May I have your full name, please?"
* "Thank you. What's your phone number?"
* "Got it. Which day works best for you?"
* "That time slot is already booked. How about 10:00 AM, 11:30 AM, or 14:00?"
* "Perfect! Booking your appointment now."
* "Your appointment is confirmed for Monday at 14:00. If you need changes, feel free to let me know."
* "The appointment is canceled successfully. Let me know if you'd like to book a new one."
* "I'm here to help. Could you please provide the date you prefer?"

French examples:
* "Bien sûr, je peux vous aider. Votre nom complet, s'il vous plaît?"
* "Merci. Votre numéro de téléphone?"
* "Ce créneau est déjà pris. Que diriez-vous de 10h00, 11h30 ou 14h00?"
* "Parfait! Je réserve votre rendez-vous maintenant."

WHAT TO AVOID:
* Long explanations
* Medical advice
* Emotional or dramatic language
* Asking too many questions at once
* Robot-like answers (like just "Name?")
* Revealing other patients' information

PRIVACY RULE:
When a time slot is taken, NEVER mention who booked it. Simply say it's unavailable and suggest alternatives.

STRUCTURED FORMAT (Add after your friendly response):

For booking:
CONFIRM_BOOKING_NOW
NAME: [full name]
PHONE: [+213...]
DATE: [day like monday/wednesday/friday]
TIME: [time like 9am/14h30]
REASON: [if provided]

For canceling:
CANCEL_APPOINTMENT_NOW
APPOINTMENT_ID: [appointment id]
PHONE: [phone number]

Remember: Be helpful, warm, and professional — like a real customer service agent, not a robot.
"""

def process_message(user_message: str, conversation_history: List[Dict[str, str]] = None) -> Dict:
    """
    Process user message with calendar integration
    """
    start_time = time.time()
    
    if conversation_history is None:
        conversation_history = []
    
    # CRITICAL: Remove any system messages from conversation history (frontend might inject them)
    conversation_history = [
        msg for msg in conversation_history 
        if msg.get('role') != 'system'
    ]
    
    try:
        print(f"\n{'='*60}")
        print(f"👤 User: {user_message}")
        print(f"{'='*60}")
        
        # Extract booking details from entire conversation
        booking_info = extract_booking_info_from_conversation(user_message, conversation_history)
        
        print(f"📊 Extracted booking info: {booking_info}")
        
        # Check if this is a cancellation request
        is_cancellation = any(word in user_message.lower() for word in ['cancel', 'annuler', 'supprimer', 'remove'])
        
        # Build messages
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        messages.extend(conversation_history)
        
        # Add context based on intent
        additional_context = ""
        
        # If cancellation and we have phone, show their appointments
        if is_cancellation and booking_info.get('phone'):
            phone = booking_info['phone']
            appointments = get_appointments_by_phone(phone)
            
            if appointments:
                additional_context += f"\n\n**📋 EXISTING APPOINTMENTS FOR {phone}:**\n"
                for apt in appointments:
                    from datetime import datetime
                    apt_time = datetime.fromisoformat(apt['start_time'])
                    formatted_time = apt_time.strftime('%A, %B %d at %I:%M %p')
                    
                    additional_context += f"- Appointment ID: {apt['id']} (DO NOT show this ID to user)\n"
                    additional_context += f"  Date: {formatted_time}\n"
                    additional_context += f"  Reason: {apt.get('reason', 'Consultation')}\n\n"
                additional_context += "⚠️ To cancel, tell the user you're canceling their appointment, then add CANCEL_APPOINTMENT_NOW with the ID at the END of your response.\n"
            else:
                additional_context += f"\n\n**❌ NO APPOINTMENTS FOUND FOR {phone}**\n"
        
        # Add calendar context if we have date/time
        calendar_context = ""
        if booking_info.get('date') and booking_info.get('time'):
            date_str = booking_info['date']
            time_str = booking_info['time']
            
            appointment_time = parse_datetime(date_str, time_str)
            
            if appointment_time:
                # Check availability
                availability = check_availability(appointment_time)
                
                calendar_context = f"\n\n**🗓️ REAL-TIME CALENDAR CHECK:**\n"
                if availability['available']:
                    calendar_context += f"✅ {date_str} at {time_str} is AVAILABLE\n"
                    
                    # Check if we have all info needed for booking
                    if booking_info.get('name') and booking_info.get('phone'):
                        calendar_context += f"\n**READY TO BOOK:**\n"
                        calendar_context += f"Name: {booking_info['name']}\n"
                        calendar_context += f"Phone: {booking_info['phone']}\n"
                        calendar_context += f"Time: {date_str} at {time_str}\n"
                        calendar_context += f"\n⚠️ Say something short like 'Booking now' then add CONFIRM_BOOKING_NOW\n"
                else:
                    # ✅ PRIVACY: Don't mention who booked it
                    calendar_context += f"❌ {date_str} at {time_str} is NOT AVAILABLE\n"
                    
                    # Get alternatives
                    available_slots = get_available_slots(appointment_time)
                    if available_slots[:3]:  # Only show 3 options
                        calendar_context += f"\n📅 Suggest these times: {', '.join(available_slots[:3])}\n"
        
        # Add user message with all context
        full_message = user_message + additional_context + calendar_context
        messages.append({
            "role": "user",
            "content": full_message
        })
        
        print(f"📤 Sending to AI with context length: {len(full_message)} chars")
        
        # Call Groq AI
        chat_completion = client.chat.completions.create(
            messages=messages,
            model=GROQ_MODEL,
            temperature=MODEL_CONFIG["temperature"],
            max_tokens=MODEL_CONFIG["max_tokens"],
            top_p=MODEL_CONFIG["top_p"]
        )
        
        assistant_message = chat_completion.choices[0].message.content
        tokens_used = chat_completion.usage.total_tokens
        duration = time.time() - start_time
        
        print(f"🤖 AI Response: {assistant_message}")
        print(f"🔢 Tokens: {tokens_used} | Duration: {duration:.2f}s")
        
        # Check if AI triggered booking with magic phrase
        booking_triggered = "CONFIRM_BOOKING_NOW" in assistant_message.upper()
        cancellation_triggered = "CANCEL_APPOINTMENT_NOW" in assistant_message.upper()
        
        print(f"🎯 Booking triggered: {booking_triggered}")
        print(f"🎯 Cancellation triggered: {cancellation_triggered}")
        
        # Attempt booking if triggered
        booking_result = None
        if booking_triggered:
            print(f"🚀 Attempting to create appointment...")
            
            # Try to extract structured data from AI response first
            structured_data = extract_structured_booking_data(assistant_message)
            
            if structured_data:
                print(f"✅ Using structured data from AI")
                booking_result = attempt_booking_with_info(structured_data)
            else:
                print(f"⚠️ No structured data, falling back to extracted info")
                booking_result = attempt_booking_with_info(booking_info)
            
            if booking_result:
                # Remove ALL structured data from user-facing response
                # Remove everything from CONFIRM_BOOKING_NOW onwards
                clean_message = re.split(r'CONFIRM_BOOKING_NOW', assistant_message, flags=re.IGNORECASE)[0]
                assistant_message = clean_message.strip() + f"\n\n{booking_result}"
        
        # Attempt cancellation if triggered
        if cancellation_triggered:
            print(f"🚀 Attempting to cancel appointment...")
            cancellation_result = attempt_cancellation(assistant_message)
            
            if cancellation_result:
                # Remove ALL structured data from user-facing response
                # Remove everything from CANCEL_APPOINTMENT_NOW onwards
                clean_message = re.split(r'CANCEL_APPOINTMENT_NOW', assistant_message, flags=re.IGNORECASE)[0]
                assistant_message = clean_message.strip() + f"\n\n{cancellation_result}"
        
        # Build updated history
        updated_history = conversation_history + [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": assistant_message}
        ]
        
        print(f"{'='*60}\n")
        
        return {
            "success": True,
            "message": assistant_message,
            "conversation_history": updated_history,
            "booking_attempted": booking_triggered,
            "booking_info": booking_info,
            "metadata": {
                "model": GROQ_MODEL,
                "tokens_used": tokens_used,
                "input_tokens": chat_completion.usage.prompt_tokens,
                "output_tokens": chat_completion.usage.completion_tokens,
                "duration": round(duration, 2)
            }
        }
        
    except Exception as e:
        duration = time.time() - start_time
        error_message = str(e)
        print(f"❌ Error: {error_message}")
        import traceback
        traceback.print_exc()
        
        if "rate_limit" in error_message.lower():
            return {
                "success": False,
                "message": "Trop de requêtes. Réessayez dans un moment / Too many requests. Try again in a moment.",
                "error": "RATE_LIMIT_EXCEEDED",
                "metadata": {"duration": round(duration, 2)}
            }
        
        return {
            "success": False,
            "message": "Erreur technique. Veuillez réessayer / Technical error. Please try again.",
            "error": error_message,
            "metadata": {"duration": round(duration, 2)}
        }

def extract_booking_info_from_conversation(current_message: str, history: List[Dict]) -> Dict:
    """
    Extract booking information from ENTIRE conversation history
    FIXED: Better name and time extraction
    """
    info = {
        'name': None,
        'phone': None,
        'date': None,
        'time': None,
        'reason': None
    }
    
    # Combine all user messages
    all_user_messages = [current_message]
    for msg in history:
        if msg['role'] == 'user':
            all_user_messages.append(msg['content'])
    
    combined_text = ' '.join(all_user_messages)
    
    print(f"🔍 Analyzing combined text: {combined_text[:200]}...")
    
    # Extract date
    days_mapping = {
        'lundi': 'monday', 'mardi': 'tuesday', 'mercredi': 'wednesday',
        'jeudi': 'thursday', 'vendredi': 'friday', 'samedi': 'saturday', 'dimanche': 'sunday',
        'monday': 'monday', 'tuesday': 'tuesday', 'wednesday': 'wednesday',
        'thursday': 'thursday', 'friday': 'friday', 'saturday': 'saturday', 'sunday': 'sunday',
        'today': 'today', 'tomorrow': 'tomorrow', "aujourd'hui": 'today', 'demain': 'tomorrow'
    }
    
    combined_lower = combined_text.lower()
    for day_pattern, day_value in days_mapping.items():
        if day_pattern in combined_lower:
            info['date'] = day_value
            print(f"✅ Found date: {day_value}")
            break
    
    # Extract time - FIXED PATTERNS
    time_patterns = [
        (r'(\d{1,2})\s*(?:h|:)\s*(\d{2})', 'time_with_minutes'),  # 9h30, 9:30
        (r'(\d{1,2})\s*(?:am|pm)', 'time_ampm'),                   # 9am, 2pm
        (r'(\d{1,2})\s*h(?:\s|$)', 'time_hour_only'),             # 9h, 14h
        (r'at\s+(\d{1,2})(?:\s|$)', 'time_at'),                   # "at 9"
        (r'(\d{1,2})(?:\s+|$)(?![\d])', 'time_standalone'),       # Just "9" 
    ]
    
    for pattern, pattern_type in time_patterns:
        match = re.search(pattern, combined_lower)
        if match:
            if pattern_type == 'time_with_minutes':
                info['time'] = f"{match.group(1)}:{match.group(2)}"
            elif pattern_type == 'time_ampm':
                info['time'] = match.group(0).strip()
            elif pattern_type == 'time_hour_only':
                info['time'] = f"{match.group(1)}h00"
            elif pattern_type == 'time_at':
                info['time'] = f"{match.group(1)}am"
            elif pattern_type == 'time_standalone':
                # Check if it's likely a time (between 1-24)
                hour = int(match.group(1))
                if 1 <= hour <= 24:
                    info['time'] = f"{hour}am" if hour <= 12 else f"{hour}:00"
            
            if info['time']:
                print(f"✅ Found time: {info['time']} (pattern: {pattern_type})")
                break
    
    # Extract phone - Algeria formats
    phone_patterns = [
        r'\+213[\s\-]?\d{9,10}',                                   # +213064795733
        r'0\d{9}',                                                  # 0XXXXXXXXX
        r'\d{10}',                                                  # 10 digits
        r'\+?\d[\d\s\-()]{8,15}'                                   # Generic
    ]
    
    for pattern in phone_patterns:
        match = re.search(pattern, combined_text)
        if match:
            phone = match.group(0).strip().replace(' ', '').replace('-', '')
            # Ensure it starts with +213
            if not phone.startswith('+'):
                if phone.startswith('213'):
                    phone = '+' + phone
                elif phone.startswith('0'):
                    phone = '+213' + phone[1:]
                else:
                    phone = '+213' + phone
            info['phone'] = phone
            print(f"✅ Found phone: {info['phone']}")
            break
    
    # Extract name - FIXED: Better patterns
    name_patterns = [
        # "my name is John Doe"
        r'(?:name is|je m\'appelle|nom[:\s]+|i am|iam|im)\s+([A-ZÀ-Üa-zà-ü]{2,}(?:\s+[A-ZÀ-Üa-zà-ü]{2,})*)',
        # "John Doe" at start of message
        r'^([A-ZÀ-Ü][a-zà-ü]+(?:\s+[A-ZÀ-Ü][a-zà-ü]+)+)',
        # Two capitalized words
        r'\b([A-ZÀ-Ü][a-zà-ü]+\s+[A-ZÀ-Ü][a-zà-ü]+)\b',
        # Single name after "my name is"
        r'(?:name is|je m\'appelle)\s+([A-ZÀ-Üa-zà-ü]{3,})',
    ]
    
    for pattern in name_patterns:
        match = re.search(pattern, combined_text, re.IGNORECASE)
        if match:
            potential_name = match.group(1).strip().title()
            # Filter out common words
            bad_words = ['the', 'is', 'am', 'are', 'my', 'your', 'book', 'appointment', 'name', 'phone', 'number']
            if not any(word in potential_name.lower() for word in bad_words):
                info['name'] = potential_name
                print(f"✅ Found name: {info['name']}")
                break
    
    # Extract reason
    reason_keywords = ['for', 'pour', 'consultation', 'check', 'checkup', 'visite', 'annual', 'control']
    for keyword in reason_keywords:
        if keyword in combined_lower:
            # Extract text after keyword
            match = re.search(f'{keyword}\\s+([a-zà-ü\\s]+?)(?:\\s+\\+|\\d|$)', combined_lower)
            if match:
                info['reason'] = match.group(1).strip()
                print(f"✅ Found reason: {info['reason']}")
                break
    
    return info

def attempt_booking_with_info(booking_info: Dict) -> Optional[str]:
    """
    Attempt to create appointment with extracted info
    Returns confirmation message or None
    """
    try:
        print(f"\n{'='*60}")
        print(f"🎯 ATTEMPTING BOOKING WITH INFO:")
        print(f"Name: {booking_info.get('name')}")
        print(f"Phone: {booking_info.get('phone')}")
        print(f"Date: {booking_info.get('date')}")
        print(f"Time: {booking_info.get('time')}")
        print(f"{'='*60}\n")
        
        # Must have all required fields
        if not all([booking_info.get('date'), booking_info.get('time'), 
                    booking_info.get('name'), booking_info.get('phone')]):
            missing = [k for k, v in booking_info.items() if not v and k in ['name', 'phone', 'date', 'time']]
            print(f"❌ Missing required fields: {missing}")
            return None
        
        # Parse datetime
        appointment_time = parse_datetime(booking_info['date'], booking_info['time'])
        if not appointment_time:
            print(f"❌ Could not parse datetime")
            return None
        
        print(f"✅ Parsed appointment time: {appointment_time}")
        
        # Create appointment
        result = create_appointment(
            patient_name=booking_info['name'],
            patient_phone=booking_info['phone'],
            start_time=appointment_time,
            duration=30,
            reason=booking_info.get('reason')
        )
        
        if result['success']:
            confirmation = f"""
✅ **RENDEZ-VOUS CONFIRMÉ / APPOINTMENT CONFIRMED**

📅 {result['start_time']}
🆔 ID: {result['appointment_id']}
👤 {booking_info['name']}
📞 {booking_info['phone']}

Un SMS de confirmation sera envoyé.
A confirmation SMS will be sent.
"""
            print(f"✅✅✅ BOOKING SUCCESSFUL!")
            return confirmation
        else:
            print(f"❌ Booking failed: {result['message']}")
            return f"\n\n❌ {result['message']}"
            
    except Exception as e:
        print(f"❌ Booking error: {e}")
        import traceback
        traceback.print_exc()
        return None

def extract_structured_booking_data(ai_response: str) -> Optional[Dict]:
    """
    Extract booking data from AI's structured output
    This is more reliable than regex on conversation history
    """
    if "CONFIRM_BOOKING_NOW" not in ai_response:
        return None
    
    try:
        # Extract the booking block
        booking_data = {}
        
        # Extract NAME
        name_match = re.search(r'NAME:\s*(.+?)(?:\n|$)', ai_response, re.IGNORECASE)
        if name_match:
            booking_data['name'] = name_match.group(1).strip()
        
        # Extract PHONE
        phone_match = re.search(r'PHONE:\s*(.+?)(?:\n|$)', ai_response, re.IGNORECASE)
        if phone_match:
            booking_data['phone'] = phone_match.group(1).strip()
        
        # Extract DATE
        date_match = re.search(r'DATE:\s*(.+?)(?:\n|$)', ai_response, re.IGNORECASE)
        if date_match:
            booking_data['date'] = date_match.group(1).strip().lower()
        
        # Extract TIME
        time_match = re.search(r'TIME:\s*(.+?)(?:\n|$)', ai_response, re.IGNORECASE)
        if time_match:
            booking_data['time'] = time_match.group(1).strip()
        
        # Extract REASON (optional)
        reason_match = re.search(r'REASON:\s*(.+?)(?:\n|$)', ai_response, re.IGNORECASE)
        if reason_match:
            booking_data['reason'] = reason_match.group(1).strip()
        
        print(f"📋 Extracted structured data: {booking_data}")
        
        # Validate we have required fields
        if all([booking_data.get('name'), booking_data.get('phone'), 
                booking_data.get('date'), booking_data.get('time')]):
            return booking_data
        else:
            print(f"⚠️ Structured data incomplete")
            return None
            
    except Exception as e:
        print(f"❌ Error extracting structured data: {e}")
        return None

def attempt_cancellation(ai_response: str) -> Optional[str]:
    """
    Extract cancellation data and cancel appointment
    """
    try:
        # Extract APPOINTMENT_ID
        id_match = re.search(r'APPOINTMENT_ID:\s*(.+?)(?:\n|$)', ai_response, re.IGNORECASE)
        if not id_match:
            print(f"❌ No appointment ID found in cancellation request")
            return None
        
        appointment_id = id_match.group(1).strip()
        
        print(f"🗑️ Canceling appointment ID: {appointment_id}")
        
        # Cancel the appointment
        result = cancel_appointment(appointment_id)
        
        if result['success']:
            return f"""
✅ **RENDEZ-VOUS ANNULÉ / APPOINTMENT CANCELED**

🆔 ID: {appointment_id}

Votre rendez-vous a été annulé avec succès.
Your appointment has been successfully canceled.
"""
        else:
            return f"\n\n❌ {result['message']}"
            
    except Exception as e:
        print(f"❌ Cancellation error: {e}")
        import traceback
        traceback.print_exc()
        return None

def analyze_intent(message: str) -> str:
    """Analyze message intent"""
    message_lower = message.lower()
    
    intents = {
        "booking": ["book", "appointment", "schedule", "reserve", "rendez-vous", "réserver"],
        "cancellation": ["cancel", "remove", "annuler", "supprimer"],
        "modification": ["change", "move", "reschedule", "modifier", "changer"],
        "question": ["what", "when", "where", "how", "qui", "quoi", "quand", "où", "comment", "price", "tarif"]
    }
    
    for intent, keywords in intents.items():
        if any(keyword in message_lower for keyword in keywords):
            return intent
    
    return "general"