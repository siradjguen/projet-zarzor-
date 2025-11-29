# app/routes/chat.py - Chat API Routes with Appointments

from fastapi import APIRouter, HTTPException
from datetime import datetime
from typing import Dict, List
from app.models import (
    ChatRequest, ChatResponse, ConversationHistory, 
    SessionsResponse, SessionInfo, ChatMessage
)
from app.agent import process_message
from app.services.calendar_service import (
    get_all_appointments, 
    clear_old_appointments,
    cancel_appointment
)

# Create router
router = APIRouter(prefix="/api", tags=["chat"])

# In-memory conversation storage
conversations: Dict[str, List[Dict[str, str]]] = {}

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint - send message to AI assistant
    
    Request body:
    - message: User's message (required)
    - session_id: Session identifier (optional, default: "default")
    
    Returns:
    - ChatResponse with AI assistant's reply
    """
    try:
        # Get conversation history for this session
        history = conversations.get(request.session_id, [])
        
        # Process with Groq AI
        result = process_message(request.message, history)
        
        # Save updated history if successful
        if result["success"] and "conversation_history" in result:
            conversations[request.session_id] = result["conversation_history"]
        
        # Build response
        return ChatResponse(
            success=result["success"],
            message=result["message"],
            session_id=request.session_id,
            timestamp=datetime.now().isoformat(),
            metadata=result.get("metadata"),
            error=result.get("error")
        )
        
    except Exception as e:
        print(f"❌ Error in chat endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": "Internal Server Error",
                "message": str(e)
            }
        )

@router.get("/conversation/{session_id}", response_model=ConversationHistory)
async def get_conversation(session_id: str):
    """
    Get conversation history for a session
    """
    history = conversations.get(session_id, [])
    
    messages = [
        ChatMessage(role=msg["role"], content=msg["content"])
        for msg in history
    ]
    
    return ConversationHistory(
        session_id=session_id,
        message_count=len(messages),
        messages=messages,
        timestamp=datetime.now().isoformat()
    )

@router.delete("/conversation/{session_id}")
async def clear_conversation(session_id: str):
    """
    Clear conversation history for a session
    """
    if session_id in conversations:
        del conversations[session_id]
        print(f"🗑️ Cleared conversation: {session_id}")
        return {
            "success": True,
            "message": "Conversation cleared",
            "session_id": session_id
        }
    else:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": "Not Found",
                "message": "Session not found"
            }
        )

@router.get("/sessions", response_model=SessionsResponse)
async def get_sessions():
    """
    Get all active sessions
    """
    sessions = []
    
    for session_id, history in conversations.items():
        last_msg = None
        if history:
            last_msg = history[-1]["content"][:50] + "..." if len(history[-1]["content"]) > 50 else history[-1]["content"]
        
        sessions.append(
            SessionInfo(
                session_id=session_id,
                message_count=len(history),
                last_message=last_msg,
                timestamp=datetime.now().isoformat()
            )
        )
    
    return SessionsResponse(
        success=True,
        total_sessions=len(sessions),
        sessions=sessions
    )

@router.delete("/conversations/all")
async def clear_all_conversations():
    """
    Clear all conversations (for testing/admin)
    """
    count = len(conversations)
    conversations.clear()
    print(f"🗑️ Cleared all {count} conversations")
    
    return {
        "success": True,
        "message": f"Cleared {count} conversations",
        "count": count
    }

# ============================================
# APPOINTMENTS ADMIN ENDPOINTS (NEW)
# ============================================

@router.get("/appointments")
async def list_all_appointments():
    """
    Get all appointments (Admin endpoint)
    
    Returns:
    - List of all appointments with details
    """
    try:
        appointments = get_all_appointments()
        
        # Format appointments for display
        formatted = []
        for apt in appointments:
            start_dt = datetime.fromisoformat(apt['start_time'])
            formatted.append({
                "id": apt['id'],
                "patient_name": apt['patient_name'],
                "patient_phone": apt['patient_phone'],
                "date": start_dt.strftime('%A, %B %d, %Y'),
                "time": start_dt.strftime('%I:%M %p'),
                "duration": f"{apt['duration']} minutes",
                "reason": apt.get('reason', 'N/A'),
                "doctor": apt.get('doctor_name', 'Any available'),
                "status": apt['status'],
                "created_at": apt['created_at']
            })
        
        return {
            "success": True,
            "count": len(formatted),
            "appointments": formatted
        }
        
    except Exception as e:
        print(f"❌ Error listing appointments: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": str(e),
                "message": "Failed to retrieve appointments"
            }
        )

@router.get("/appointments/{phone}")
async def get_patient_appointments(phone: str):
    """
    Get appointments for a specific phone number
    
    Path parameters:
    - phone: Patient's phone number
    """
    try:
        from app.services.calendar_service import get_appointments_by_phone
        
        appointments = get_appointments_by_phone(phone)
        
        formatted = []
        for apt in appointments:
            start_dt = datetime.fromisoformat(apt['start_time'])
            formatted.append({
                "id": apt['id'],
                "date": start_dt.strftime('%A, %B %d, %Y'),
                "time": start_dt.strftime('%I:%M %p'),
                "reason": apt.get('reason', 'N/A'),
                "status": apt['status']
            })
        
        return {
            "success": True,
            "phone": phone,
            "count": len(formatted),
            "appointments": formatted
        }
        
    except Exception as e:
        print(f"❌ Error getting patient appointments: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/appointments/{appointment_id}")
async def delete_appointment(appointment_id: str):
    """
    Cancel/delete an appointment
    
    Path parameters:
    - appointment_id: Appointment ID to cancel
    """
    try:
        result = cancel_appointment(appointment_id)
        
        if result["success"]:
            return result
        else:
            raise HTTPException(
                status_code=404,
                detail=result
            )
            
    except Exception as e:
        print(f"❌ Error cancelling appointment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/appointments/cleanup")
async def cleanup_old_appointments():
    """
    Remove old/past appointments
    """
    try:
        clear_old_appointments()
        return {
            "success": True,
            "message": "Old appointments cleaned up"
        }
    except Exception as e:
        print(f"❌ Error cleaning appointments: {e}")
        raise HTTPException(status_code=500, detail=str(e))