"""
Groq LLM Client - Fixed Cancel/Edit Flow
"""

import json
from typing import Dict, List, Any, Optional
from groq import Groq
import os

from app.config import GROQ_API_KEY, GROQ_MODEL

class GroqAgent:
    """
    LLM Agent for natural language understanding and generation
    """
    
    def __init__(self):
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY environment variable not set")
        
        self.client = Groq(api_key=GROQ_API_KEY)
        self.model = GROQ_MODEL
        print(f"[+] Groq LLM Agent initialized (model: {self.model})")
    
    async def extract_entities(
        self,
        message: str,
        intent: str,
        conversation_history: List[Dict[str, Any]] = None,
        accumulated_entities: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Extract structured entities from user message
        """
        
        system_prompt = """You are an entity extraction AI for a medical clinic.
Extract relevant information from user messages and return ONLY valid JSON.

CRITICAL RULES:
1. Extract ALL entities mentioned in the current message
2. Return ONLY NEW or UPDATED entities from this message
3. If a field isn't mentioned in THIS message, omit it from your response
4. Don't repeat entities that were already collected unless the user is correcting them

Extract these fields when present:
- patient_name: full name
- patient_phone: phone number (format: 10 digits)
- date: date mentioned (keep original format like "28 december", "monday", "6 january 2026")
- time: time mentioned (keep original format like "10", "1", "10 in the morning")
- doctor_name: doctor's name if mentioned (e.g., "Dr. Smith", "Doctor Ahmed", "Dr. Sarah")
- reason: reason for visit (e.g., "checkup", "consultation", "dental", "follow-up", "covid test")
- appointment_id: appointment ID if mentioned

Return ONLY a JSON object with extracted fields from THIS MESSAGE ONLY.

Examples:
User: "Book for John Doe"
Response: {"patient_name": "John Doe"}

User: "with Dr. Ahmed for a checkup"
Response: {"doctor_name": "Dr. Ahmed", "reason": "checkup"}

User: "0543698720"
Response: {"patient_phone": "0543698720"}

User: "yes" (when confirming)
Response: {}"""

        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add accumulated context so LLM knows what's already collected
        context_info = ""
        if accumulated_entities:
            context_info = f"\n\nAlready collected: {json.dumps(accumulated_entities)}"
        
        # Add recent conversation history
        if conversation_history:
            for msg in conversation_history[-3:]:
                messages.append(msg)
        
        messages.append({
            "role": "user",
            "content": f"Intent: {intent}\nCurrent message: {message}{context_info}\n\nExtract NEW entities from current message as JSON:"
        })
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1,
                max_tokens=500
            )
            
            content = response.choices[0].message.content.strip()
            
            # Parse JSON response
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            entities = json.loads(content)
            print(f"✅ Extracted entities: {entities}")
            return entities
            
        except json.JSONDecodeError as e:
            print(f"⚠️ Failed to parse LLM JSON response: {e}")
            return {}
        except Exception as e:
            print(f"❌ LLM extraction error: {e}")
            return {}
    
    async def generate_response(
        self,
        context: Dict[str, Any],
        conversation_history: List[Dict[str, Any]] = None
    ) -> str:
        """
        Generate professional medical clinic response
        """
        
        system_prompt = """You are MediBook Clinic's AI Assistant.

CANCEL APPOINTMENT FLOW:
1. User says "cancel" → Ask for phone number
2. User provides phone → Look up appointment and show details, then ask "Are you sure you want to cancel this appointment? (yes/no)"
3. User says "yes" → Execute cancellation and confirm
4. User says "no" → Cancel the operation

EDIT APPOINTMENT FLOW:
1. User says "edit" → Ask for phone number
2. User provides phone → Ask what they want to change (date, time, doctor, reason)
3. User provides changes → Confirm the changes
4. User says "yes" → Execute update and confirm

BOOKING FLOW:
1. User says "book" → Ask for: name, phone, date, time, doctor (optional), reason (optional)
2. Collect all required info
3. Summarize and ask for confirmation
4. User confirms → Execute booking

VIEW APPOINTMENTS:
When user provides phone for viewing, show all their appointments clearly.

RESPONSE PATTERNS:

When CANCEL requested and NO phone yet:
"To cancel your appointment, I'll need your phone number please."

When CANCEL and phone provided and appointments FOUND:
"I found your appointment:
• Patient: {name}
• Date: {date}
• Time: {time}
• Doctor: {doctor}
• Reason: {reason}

Are you sure you want to cancel this appointment? (yes/no)"

When user confirms CANCEL with "yes":
"✅ Your appointment has been cancelled successfully. Is there anything else I can help you with?"

When CANCEL but NO appointments found:
"I couldn't find any appointments for phone number {phone}. Please verify your phone number or check if you have any upcoming appointments."

When EDIT requested:
"To modify your appointment, please provide your phone number."

After providing phone for EDIT:
"What would you like to change? You can update the date, time, doctor, or reason for your visit."

ABSOLUTE RULES:
❌ NEVER say "processing" or "retrieving" - just ask for what you need
❌ NEVER ask for info that's already provided
✅ ALWAYS show appointment details before asking for cancel confirmation
✅ ALWAYS be clear and direct"""

        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add conversation history
        if conversation_history:
            for msg in conversation_history[-5:]:
                messages.append(msg)
        
        # Build current context
        user_message = context.get("message", "")
        intent = context.get("intent", "")
        action_result = context.get("action_result", {})
        collected_data = context.get("collected_data", {})
        awaiting_confirmation = context.get("awaiting_confirmation")
        pending_action = context.get("pending_action")
        
        prompt_parts = [
            f"User's message: \"{user_message}\"",
            f"Intent: {intent}",
            f"\nCollected data: {json.dumps(collected_data)}"
        ]
        
        # Handle action results
        if action_result:
            if action_result.get("success"):
                if intent == "cancel":
                    # Check if this is the view result (before confirmation) or actual cancel result
                    if awaiting_confirmation == 'cancel' and action_result.get('appointments'):
                        # Show appointment details and ask for confirmation
                        appointments = action_result.get('appointments', [])
                        if appointments:
                            apt = appointments[0]  # Get first/upcoming appointment
                            prompt_parts.append(f"\n✅ FOUND APPOINTMENT TO CANCEL:")
                            prompt_parts.append(f"Patient: {apt.get('patient_name')}")
                            prompt_parts.append(f"Phone: {apt.get('patient_phone')}")
                            prompt_parts.append(f"Date: {apt.get('start_time')}")
                            prompt_parts.append(f"Doctor: {apt.get('doctor_name', 'Not specified')}")
                            prompt_parts.append(f"Reason: {apt.get('reason', 'Not specified')}")
                            prompt_parts.append("\nShow these details and ask: 'Are you sure you want to cancel this appointment? (yes/no)'")
                    else:
                        # Actual cancellation happened
                        prompt_parts.append(f"\n✅ CANCELLATION SUCCESSFUL")
                        prompt_parts.append("Confirm the cancellation and ask if they need anything else.")
                
                elif intent == "view":
                    appointments = action_result.get('appointments', [])
                    prompt_parts.append(f"\n📋 FOUND {len(appointments)} APPOINTMENTS")
                    for apt in appointments:
                        prompt_parts.append(f"  - {apt.get('patient_name')} on {apt.get('start_time')}")
                
                elif intent == "edit":
                    # Check if this is the view result (before user specifies changes) or actual edit result
                    if awaiting_confirmation == 'edit':
                        # User confirmed edit
                        prompt_parts.append(f"\n✅ UPDATE SUCCESSFUL")
                        prompt_parts.append("Confirm the update to the user.")
                    elif action_result.get('appointments'):
                        # Show appointment details and ask what to change
                        appointments = action_result.get('appointments', [])
                        if appointments:
                            apt = appointments[0]
                            prompt_parts.append(f"\n✅ FOUND APPOINTMENT TO EDIT:")
                            prompt_parts.append(f"Patient: {apt.get('patient_name')}")
                            prompt_parts.append(f"Phone: {apt.get('patient_phone')}")
                            prompt_parts.append(f"Date: {apt.get('start_time')}")
                            prompt_parts.append(f"Doctor: {apt.get('doctor_name', 'Not specified')}")
                            prompt_parts.append(f"Reason: {apt.get('reason', 'Not specified')}")
                            prompt_parts.append("\nShow these details and ask: 'What would you like to change? (date, time, doctor, or reason)'")
                
                elif intent == "book":
                    prompt_parts.append(f"\n✅ BOOKING SUCCESSFUL")
                    prompt_parts.append(f"ID: {action_result.get('appointment_id')}")
            else:
                error_msg = action_result.get('message', 'Unknown error')
                prompt_parts.append(f"\n❌ ERROR: {error_msg}")
        
        # Handle awaiting confirmation
        if awaiting_confirmation:
            prompt_parts.append(f"\n⏳ AWAITING CONFIRMATION for: {awaiting_confirmation}")
        
        # Handle pending action
        if pending_action and not awaiting_confirmation:
            prompt_parts.append(f"\n🔄 PENDING ACTION: {pending_action}")
            if pending_action == 'cancel' and not collected_data.get('patient_phone'):
                prompt_parts.append("Ask for phone number to proceed with cancellation.")
            elif pending_action == 'edit' and not collected_data.get('patient_phone'):
                prompt_parts.append("Ask for phone number to proceed with edit.")
        
        final_prompt = "\n".join(prompt_parts)
        messages.append({"role": "user", "content": final_prompt})
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=400
            )
            
            reply = response.choices[0].message.content.strip()
            print(f"✅ Generated response: {reply[:100]}...")
            return reply
            
        except Exception as e:
            print(f"❌ LLM generation error: {e}")
            return "I apologize, but I'm having trouble processing your request. Please try again."
    
    async def generate_greeting(self) -> str:
        """Generate a professional greeting"""
        return "Hello! Welcome to MediBook Clinic. How may I assist you today?"
    
    async def generate_goodbye(self) -> str:
        """Generate a professional goodbye"""
        return "Thank you for choosing MediBook Clinic. Take care and stay healthy!"
    
    async def generate_help(self) -> str:
        """Generate help message"""
        return """I can assist you with:

• Book a new appointment
• View your appointments
• Modify an appointment
• Cancel an appointment

What would you like to do?"""

print("[+] Groq LLM Agent loaded")