"""
FastAPI Entry Point - Fixed Response Handling
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uvicorn

from mcp.server import MCPServer

# Initialize FastAPI app
app = FastAPI(
    title="MediBook Clinic API",
    description="AI-powered medical appointment booking system",
    version="2.0.0"
)

# CORS middleware (allow frontend to connect)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize MCP Server
mcp_server = MCPServer()

# Request/Response models
class ChatRequest(BaseModel):
    message: str
    session_id: str

class ChatResponse(BaseModel):
    response: str
    intent: Optional[str] = None
    entities: Optional[Dict[str, Any]] = None

# Health check endpoint
@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "MediBook Clinic API",
        "version": "2.0.0",
        "architecture": "FastAPI -> MCP Server -> LLM Agent -> Tools"
    }

# Main chat endpoint
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint
    
    Receives user message and session ID
    Returns bot response with intent and entities
    """
    try:
        # Validate input
        if not request.message or not request.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        if not request.session_id:
            raise HTTPException(status_code=400, detail="Session ID required")
        
        # Process through MCP Server
        result = await mcp_server.process_message(
            message=request.message,
            session_id=request.session_id
        )
        
        # Extract response from result dict
        # MCP returns: {"response": str, "intent": str, "entities": dict, ...}
        return ChatResponse(
            response=result.get("response", "I apologize, but I couldn't process that."),
            intent=result.get("intent"),
            entities=result.get("entities")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Session management endpoint (optional - for clearing sessions)
@app.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """Clear a specific session"""
    try:
        mcp_server.clear_session(session_id)
        return {"status": "success", "message": f"Session {session_id} cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Startup event
@app.on_event("startup")
async def startup_event():
    print("[+] Starting MediBook Clinic API...")
    print("[*] Architecture: FastAPI -> MCP Server -> LLM Agent -> Tools")

# Run server
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )