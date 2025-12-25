"""
MCP Server Module - FIXED Edit Flow (Context-Aware Intent Detection)
"""

from typing import Dict, List, Any
from llm.groq_client import GroqAgent
from services.appointment_service import AppointmentService
from mcp.intents import Intent, IntentDetector

class MCPServer:
    """
    Model Context Protocol Server - Fixed Edit with Context-Aware Intent Detection
    """
    
    def __init__(self):
        self.llm = GroqAgent()
        self.intent_detector = IntentDetector()
        
        # Session storage
        self.sessions: Dict[str, Dict[str, Any]] = {}
        
        print("[+] MCP Server initialized (FIXED: Context-Aware)")
    
    def _get_or_create_session(self, session_id: str) -> Dict[str, Any]:
        """Get or create session data"""
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "history": [],
                "entities": {},
                "last_intent": None,
                "awaiting_confirmation": None,
                "pending_action": None,
                "edit_stage": None
            }
            print(f"🆕 New session: {session_id}")
        return self.sessions[session_id]
    
    async def process_message(self, message: str, session_id: str) -> Dict[str, Any]:
        """Main orchestration method - FIXED Edit Flow with Context-Aware Intent Detection"""
        
        print(f"\n{'='*60}")
        print(f"🎯 Processing: '{message}' (session: {session_id[:8]})")
        print(f"{'='*60}")
        
        session = self._get_or_create_session(session_id)
        
        # Check if user is confirming/canceling
        confirm_words = ['yes', 'confirm', 'ok', 'correct', 'right', 'yep', 'yeah', 'oui', 'si', 'good', 'sure', 'proceed']
        cancel_words = ['no', 'cancel', 'nope', 'nah', 'stop', 'non', 'don\'t']
        message_lower = message.lower()
        is_confirming = any(word in message_lower for word in confirm_words)
        is_canceling_confirmation = any(word in message_lower for word in cancel_words) and not is_confirming
        
        print(f"[DEBUG] Pending Action: {session.get('pending_action')}")
        print(f"[DEBUG] Awaiting: {session.get('awaiting_confirmation')}")
        print(f"[DEBUG] Edit Stage: {session.get('edit_stage')}")
        print(f"[DEBUG] Is Confirming: {is_confirming}, Is Canceling: {is_canceling_confirmation}")
        print(f"[DEBUG] Entities: {session['entities']}")
        
        # Handle confirmations FIRST
        if session.get('awaiting_confirmation') and is_confirming:
            confirmation_type = session['awaiting_confirmation']
            phone = session['entities'].get('patient_phone')
            
            print(f"✓ User confirmed: {confirmation_type}")
            
            action_result = None
            
            if confirmation_type == 'cancel' and phone:
                print("✓ Executing cancel")
                action_result = await AppointmentService.cancel_appointment_by_phone(phone)
                session['awaiting_confirmation'] = None
                session['pending_action'] = None
            
            elif confirmation_type == 'edit' and phone:
                # Check if we have actual new values before executing
                date_val = session['entities'].get('date')
                time_val = session['entities'].get('time')
                
                # Check for valid date (not placeholder)
                has_new_date = date_val and date_val != 'date'
                has_new_time = time_val
                
                # Valid if we have date OR time OR both
                has_new_date_time = has_new_date or has_new_time
                has_new_doctor = session['entities'].get('doctor_name')
                has_new_reason = session['entities'].get('reason')
                
                has_valid_changes = has_new_date_time or has_new_doctor or has_new_reason
                
                if has_valid_changes:
                    print("✓ Executing edit with valid changes")
                    action_result = await self._handle_edit(session['entities'])
                    session['awaiting_confirmation'] = None
                    session['pending_action'] = None
                    session['edit_stage'] = None
                else:
                    # User confirmed but didn't provide the actual changes yet
                    print("⏳ User confirmed edit intent, now collecting new values")
                    session['awaiting_confirmation'] = None
                    session['edit_stage'] = 'collecting_changes'
                    
                    response = "Great! What would you like to change? Please provide the new date, time, doctor, or reason."
                    
                    session['history'].append({"role": "user", "content": message})
                    session['history'].append({"role": "assistant", "content": response})
                    
                    return {
                        "response": response,
                        "intent": "edit",
                        "entities": session['entities']
                    }
            
            elif confirmation_type == 'book':
                print("✓ Executing booking")
                action_result = await self._handle_booking(session['entities'])
                session['awaiting_confirmation'] = None
                session['pending_action'] = None
            
            # Generate response with action result
            response = await self.llm.generate_response(
                context={
                    "message": message,
                    "intent": confirmation_type,
                    "collected_data": session['entities'],
                    "action_result": action_result,
                    "awaiting_confirmation": None,
                    "edit_stage": session.get('edit_stage')
                },
                conversation_history=session['history']
            )
            
            session['history'].append({"role": "user", "content": message})
            session['history'].append({"role": "assistant", "content": response})
            
            # Clear entities after successful action
            if action_result and action_result.get('success'):
                session['entities'] = {}
                session['edit_stage'] = None
            
            return {
                "response": response,
                "intent": confirmation_type,
                "entities": session['entities'],
                "action_result": action_result
            }
        
        # Handle cancel confirmation rejection
        if session.get('awaiting_confirmation') and is_canceling_confirmation:
            confirmation_type = session['awaiting_confirmation']
            session['awaiting_confirmation'] = None
            session['pending_action'] = None
            session['edit_stage'] = None
            
            response = f"Okay, I've cancelled the {confirmation_type} operation. Is there anything else I can help you with?"
            
            session['history'].append({"role": "user", "content": message})
            session['history'].append({"role": "assistant", "content": response})
            
            return {
                "response": response,
                "intent": "confirmation_cancelled",
                "entities": session['entities']
            }
        
        # FIXED: Handle edit stages where we're collecting changes
        if session.get('edit_stage') in ['shown_appointment', 'collecting_changes']:
            print(f"[*] In edit stage '{session.get('edit_stage')}', processing: {message}")
            
            # Transition to collecting_changes if we were just showing the appointment
            if session.get('edit_stage') == 'shown_appointment':
                session['edit_stage'] = 'collecting_changes'
                print("[*] Transitioned to 'collecting_changes' stage")
            
            # Extract new values
            extracted_entities = await self.llm.extract_entities(
                message=message,
                intent='edit',
                conversation_history=session['history'],
                accumulated_entities=session['entities']
            )
            
            session['entities'].update(extracted_entities)
            print(f"✅ Extracted entities: {extracted_entities}")
            print(f"📦 Updated entities: {session['entities']}")
            
            # Check if we now have valid changes
            phone = session['entities'].get('patient_phone')
            
            # Check for new date (with or without time)
            has_new_date = (
                session['entities'].get('date') and 
                session['entities'].get('date') != 'date'
            )
            
            # Check for new time
            has_new_time = session['entities'].get('time')
            
            # Valid if we have date OR time OR both
            has_new_date_time = has_new_date or has_new_time
            
            has_new_doctor = session['entities'].get('doctor_name')
            has_new_reason = session['entities'].get('reason')
            
            has_valid_changes = has_new_date_time or has_new_doctor or has_new_reason
            
            if has_valid_changes:
                # Now ask for final confirmation
                session['awaiting_confirmation'] = 'edit'
                session['edit_stage'] = 'awaiting_final_confirmation'
                
                response = await self.llm.generate_response(
                    context={
                        "message": message,
                        "intent": "edit",
                        "collected_data": session['entities'],
                        "awaiting_confirmation": "edit",
                        "edit_stage": "awaiting_final_confirmation"
                    },
                    conversation_history=session['history']
                )
            else:
                # Still need more info
                response = "I need more details. Please provide the new date and time (e.g., '21 january 2026 at 10am'), or specify the doctor or reason."
            
            session['history'].append({"role": "user", "content": message})
            session['history'].append({"role": "assistant", "content": response})
            
            return {
                "response": response,
                "intent": "edit",
                "entities": session['entities']
            }
        
        # Step 1: Detect intent WITH SESSION CONTEXT (FIXED)
        intent = self.intent_detector.detect(
            message,
            session_context={
                'edit_stage': session.get('edit_stage'),
                'pending_action': session.get('pending_action'),
                'awaiting_confirmation': session.get('awaiting_confirmation')
            }
        )
        print(f"📋 Detected intent: {intent.value}")
        
        # If intent is unclear but we have a pending action, use that context
        if intent == Intent.UNCLEAR and session.get('pending_action'):
            print(f"[*] Using pending action context: {session['pending_action']}")
            intent = Intent(session['pending_action'])
        
        session['last_intent'] = intent.value
        
        # Handle simple intents
        if intent == Intent.GREET:
            response = await self.llm.generate_greeting()
            return {"response": response, "intent": intent.value}
        
        if intent == Intent.GOODBYE:
            response = await self.llm.generate_goodbye()
            if session_id in self.sessions:
                del self.sessions[session_id]
            return {"response": response, "intent": intent.value}
        
        if intent == Intent.HELP:
            response = await self.llm.generate_help()
            return {"response": response, "intent": intent.value}
        
        # Step 2: Extract entities
        extracted_entities = {}
        if self.intent_detector.requires_llm(intent):
            print("🤖 Calling LLM for entity extraction...")
            extracted_entities = await self.llm.extract_entities(
                message=message,
                intent=intent.value,
                conversation_history=session['history'],
                accumulated_entities=session['entities']
            )
            
            session['entities'].update(extracted_entities)
            print(f"✅ Extracted entities: {extracted_entities}")
            print(f"📦 Accumulated entities: {session['entities']}")
        
        # Step 3: Execute or prepare actions
        action_result = None
        phone = session['entities'].get('patient_phone')
        
        # BOOKING
        if intent == Intent.BOOK:
            session['pending_action'] = 'book'
            required = ['patient_name', 'patient_phone', 'date', 'time']
            has_all = all(f in session['entities'] and session['entities'][f] for f in required)
            
            if has_all and not session.get('awaiting_confirmation'):
                session['awaiting_confirmation'] = 'book'
                print("⏳ Ready to book - asking for confirmation")
        
        # VIEW
        elif intent == Intent.VIEW:
            session['pending_action'] = 'view'
            if phone:
                print("✓ Viewing appointments")
                action_result = await AppointmentService.view_appointments(phone)
                session['pending_action'] = None
        
        # EDIT - FIXED FLOW
        elif intent == Intent.EDIT:
            session['pending_action'] = 'edit'
            
            if not phone:
                # Need phone first
                print("⏳ Need phone for edit")
            
            elif not session.get('awaiting_confirmation') and not session.get('edit_stage'):
                # Stage 1: Show appointment and ask what to change
                print(f"[*] Stage 1: Showing appointments for phone: {phone}")
                view_result = await AppointmentService.view_appointments(phone)
                
                if view_result.get('success') and view_result.get('appointments'):
                    action_result = view_result
                    session['edit_stage'] = 'shown_appointment'
                    print("📋 Showing appointment, asking what to change")
                else:
                    action_result = {
                        "success": False,
                        "message": f"No appointments found for phone number {phone}"
                    }
                    session['pending_action'] = None
        
        # CANCEL
        elif intent == Intent.CANCEL:
            session['pending_action'] = 'cancel'
            if not phone:
                print("⏳ Need phone for cancel")
            elif not session.get('awaiting_confirmation'):
                print(f"[*] Checking appointments for phone: {phone}")
                view_result = await AppointmentService.view_appointments(phone)
                
                if view_result.get('success') and view_result.get('appointments'):
                    session['awaiting_confirmation'] = 'cancel'
                    action_result = view_result
                    print("⏳ Ready to cancel - asking for confirmation")
                else:
                    action_result = {
                        "success": False,
                        "message": f"No appointments found for phone number {phone}"
                    }
                    session['pending_action'] = None
        
        # Step 4: Generate response
        print("💬 Generating response...")
        response = await self.llm.generate_response(
            context={
                "message": message,
                "intent": intent.value,
                "collected_data": session['entities'],
                "action_result": action_result,
                "awaiting_confirmation": session.get('awaiting_confirmation'),
                "pending_action": session.get('pending_action'),
                "edit_stage": session.get('edit_stage')
            },
            conversation_history=session['history']
        )
        
        # Step 5: Update history
        session['history'].append({"role": "user", "content": message})
        session['history'].append({"role": "assistant", "content": response})
        
        if len(session['history']) > 10:
            session['history'] = session['history'][-10:]
        
        print(f"✅ Generated response: {response[:100]}...")
        print(f"✅ Response: {response[:100]}...")
        print(f"{'='*60}\n")
        
        return {
            "response": response,
            "intent": intent.value,
            "entities": session['entities'],
            "action_result": action_result
        }
    
    async def _handle_booking(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Handle booking"""
        required = ['patient_name', 'patient_phone', 'date', 'time']
        missing = [f for f in required if f not in entities or not entities[f]]
        
        if missing:
            return {
                "success": False,
                "missing_fields": missing,
                "message": f"Still need: {', '.join(missing)}"
            }
        
        try:
            print(f"[*] Booking: {entities}")
            return await AppointmentService.book_appointment(
                patient_name=entities['patient_name'],
                patient_phone=entities['patient_phone'],
                date=entities['date'],
                time=entities['time'],
                reason=entities.get('reason', 'General consultation'),
                doctor_name=entities.get('doctor_name', 'Any available doctor')
            )
        except Exception as e:
            print(f"❌ Booking error: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "message": f"Error: {str(e)}"}
    
    async def _handle_edit(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Handle edit - FIXED to handle date-only or time-only changes"""
        phone = entities.get('patient_phone')
        if not phone:
            return {"success": False, "message": "Phone number required"}
        
        # Get the current appointment to preserve existing values
        print(f"[*] Editing for phone: {phone}")
        view_result = await AppointmentService.view_appointments(phone)
        if not view_result.get('success') or not view_result.get('appointments'):
            return {"success": False, "message": "No appointments found"}
        
        current_apt = view_result['appointments'][0]
        
        # Validate that we have actual changes (not placeholder values)
        date_val = entities.get('date')
        time_val = entities.get('time')
        
        # Check if date is a placeholder
        if date_val and date_val == 'date':
            return {
                "success": False,
                "message": "Please provide the actual new date (e.g., '21 january 2026')"
            }
        
        # If only date is provided (no time), extract time from current appointment
        if date_val and not time_val:
            from datetime import datetime
            current_start = datetime.fromisoformat(current_apt['start_time'])
            time_val = current_start.strftime('%H:%M')
            print(f"[*] Using existing time: {time_val}")
        
        # If only time is provided (no date), extract date from current appointment
        if time_val and not date_val:
            from datetime import datetime
            current_start = datetime.fromisoformat(current_apt['start_time'])
            date_val = current_start.strftime('%Y-%m-%d')
            print(f"[*] Using existing date: {date_val}")
        
        try:
            print(f"[*] Changes: date={date_val}, time={time_val}, doctor={entities.get('doctor_name')}, reason={entities.get('reason')}")
            
            return await AppointmentService.update_appointment_by_phone(
                phone=phone,
                new_date=date_val,
                new_time=time_val,
                new_doctor=entities.get('doctor_name'),
                new_reason=entities.get('reason')
            )
        except Exception as e:
            print(f"❌ Edit error: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "message": f"Error: {str(e)}"}
    
    def clear_session(self, session_id: str):
        """Clear a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            print(f"🗑️ Cleared session: {session_id}")

print("[+] MCP Server module loaded (FIXED: Context-Aware Intent Detection)")