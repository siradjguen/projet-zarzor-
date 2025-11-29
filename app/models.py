# app/models.py - Pydantic Data Models

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime

class ChatMessage(BaseModel):
    """Chat message model"""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")

class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    message: str = Field(..., min_length=1, max_length=5000, description="User message")
    session_id: Optional[str] = Field(default="default", max_length=100, description="Session identifier")
    
    @validator('message')
    def message_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Message cannot be empty')
        return v.strip()
    
    @validator('session_id')
    def session_id_valid(cls, v):
        if v and len(v) > 100:
            raise ValueError('Session ID too long')
        return v or "default"

class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    success: bool = Field(..., description="Whether the request was successful")
    message: str = Field(..., description="AI assistant response")
    session_id: str = Field(..., description="Session identifier")
    timestamp: str = Field(..., description="Response timestamp")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    error: Optional[str] = Field(default=None, description="Error message if failed")

class ConversationHistory(BaseModel):
    """Conversation history model"""
    session_id: str = Field(..., description="Session identifier")
    message_count: int = Field(..., description="Number of messages")
    messages: List[ChatMessage] = Field(..., description="List of messages")
    timestamp: str = Field(..., description="Timestamp")

class HealthResponse(BaseModel):
    """Health check response model"""
    success: bool = True
    status: str = "healthy"
    timestamp: str
    uptime: float
    environment: str
    groq: Dict[str, Any]
    server: Dict[str, Any]

class ErrorResponse(BaseModel):
    """Error response model"""
    success: bool = False
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Any] = Field(default=None, description="Additional error details")

class SessionInfo(BaseModel):
    """Session information model"""
    session_id: str
    message_count: int
    last_message: Optional[str] = None
    timestamp: str

class SessionsResponse(BaseModel):
    """Sessions list response model"""
    success: bool = True
    total_sessions: int
    sessions: List[SessionInfo]