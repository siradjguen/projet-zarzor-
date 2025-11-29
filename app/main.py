# app/main.py - FastAPI Main Server

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
import time
import psutil
import sys

from app.config import CORS_ORIGINS, ENVIRONMENT, validate_config, GROQ_MODEL, GROQ_API_KEY
from app.routes import chat
from app.models import HealthResponse, ErrorResponse

# Validate configuration on startup
validate_config()

# Initialize FastAPI app
app = FastAPI(
    title="Medical AI Assistant API",
    description="AI-powered medical appointment assistant with Groq (Llama 3.3 70B)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Track server start time
start_time = time.time()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests"""
    start = time.time()
    
    # Log request
    print(f"\n→ {request.method} {request.url.path}")
    
    # Process request
    response = await call_next(request)
    
    # Log response
    duration = time.time() - start
    print(f"← {response.status_code} ({duration:.2f}s)")
    
    return response

# Include routers
app.include_router(chat.router)

# ===== ROOT ENDPOINTS =====

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "success": True,
        "service": "Medical AI Assistant API",
        "version": "1.0.0",
        "model": "Llama 3.3 70B Versatile (Groq)",
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc",
            "health": "GET /health",
            "chat": "POST /api/chat",
            "conversation": "GET /api/conversation/{session_id}",
            "clear_session": "DELETE /api/conversation/{session_id}",
            "sessions": "GET /api/sessions"
        }
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    process = psutil.Process()
    memory_info = process.memory_info()
    
    return HealthResponse(
        success=True,
        status="healthy",
        timestamp=datetime.now().isoformat(),
        uptime=round(time.time() - start_time, 2),
        environment=ENVIRONMENT,
        groq={
            "configured": bool(GROQ_API_KEY),
            "model": GROQ_MODEL
        },
        server={
            "python_version": sys.version.split()[0],
            "memory_used_mb": round(memory_info.rss / 1024 / 1024, 2),
            "cpu_percent": process.cpu_percent()
        }
    )

# ===== ERROR HANDLERS =====

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors"""
    return JSONResponse(
        status_code=404,
        content={
            "success": False,
            "error": "Not Found",
            "message": f"Cannot {request.method} {request.url.path}",
            "available_endpoints": [
                "GET /health",
                "POST /api/chat",
                "GET /api/conversation/{session_id}",
                "DELETE /api/conversation/{session_id}",
                "GET /api/sessions"
            ]
        }
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Handle 500 errors"""
    print(f"❌ Internal Server Error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal Server Error",
            "message": "Something went wrong. Please try again later."
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    print(f"❌ Unhandled Exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal Server Error",
            "message": str(exc) if ENVIRONMENT == "development" else "An unexpected error occurred"
        }
    )

# ===== STARTUP EVENT =====

@app.on_event("startup")
async def startup_event():
    """Print banner on startup"""
    print("""
╔═══════════════════════════════════════════════════╗
║  🏥 Medical AI Assistant - Python Backend        ║
║                                                   ║
║  🐍 FastAPI + Groq                               ║
║  🤖 Model: Llama 3.3 70B Versatile               ║
║  💰 Cost: FREE                                    ║
║  ⚡ Status: Ready                                 ║
║                                                   ║
║  📡 Docs: http://localhost:8000/docs             ║
╚═══════════════════════════════════════════════════╝
    """)
    
    if not GROQ_API_KEY:
        print("⚠️  WARNING: GROQ_API_KEY not set!")
        print("Get your FREE key at: https://console.groq.com/\n")
    else:
        print("✅ Groq API key configured\n")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("\n🛑 Server shutting down...")
    print("✅ Cleanup completed")