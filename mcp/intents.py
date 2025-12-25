"""
Intent Detection Module - FIXED: Context-Aware Detection
MCP Server uses this to classify user intentions
"""

from enum import Enum
from typing import Dict, Optional

class Intent(Enum):
    """User intent categories"""
    GREET = "greet"
    BOOK = "book"
    EDIT = "edit"
    CANCEL = "cancel"
    VIEW = "view"
    GOODBYE = "goodbye"
    UNCLEAR = "unclear"
    HELP = "help"

class IntentDetector:
    """
    Rule-based intent detection with context awareness
    MCP Server uses this BEFORE deciding whether to call LLM
    """
    
    # Intent keywords (simple rule-based detection)
    INTENT_KEYWORDS = {
        Intent.GREET: [
            'hello', 'hi', 'hey', 'good morning', 'good afternoon',
            'bonjour', 'salut', 'salam'
        ],
        Intent.BOOK: [
            'book', 'schedule', 'appointment', 'make', 'reserve',
            'réserver', 'rendez-vous', 'prendre'
        ],
        Intent.EDIT: [
            'change', 'modify', 'reschedule', 'update', 'edit',
            'move', 'changer', 'modifier'
        ],
        Intent.CANCEL: [
            'cancel', 'delete', 'remove', 'annuler', 'supprimer'
        ],
        Intent.VIEW: [
            'view', 'show', 'list', 'my appointments', 'check',
            'voir', 'afficher', 'mes rendez-vous'
        ],
        Intent.GOODBYE: [
            'bye', 'goodbye', 'see you', 'thanks', 'thank you',
            'au revoir', 'merci', 'bye bye'
        ],
        Intent.HELP: [
            'help', 'what can you do', 'options', 'aide', 'comment'
        ]
    }
    
    @staticmethod
    def detect(message: str, session_context: Optional[Dict] = None) -> Intent:
        """
        Detect intent from user message with optional session context
        
        Args:
            message: User's message
            session_context: Optional dict with keys like:
                - edit_stage: Current edit stage
                - pending_action: Pending action
                - awaiting_confirmation: What we're waiting confirmation for
        
        FIXED: Now context-aware - if user is in edit flow, ambiguous
        phrases like "make it 10" are treated as edit, not new booking
        """
        message_lower = message.lower().strip()
        
        # CONTEXT-AWARE LOGIC: If in edit flow, override detection
        if session_context:
            edit_stage = session_context.get('edit_stage')
            
            # If user is in active edit flow
            if edit_stage in ['shown_appointment', 'collecting_changes', 'awaiting_final_confirmation']:
                # Check if user explicitly wants to cancel or exit
                exit_words = ['cancel', 'bye', 'goodbye', 'stop', 'quit', 'exit', 'annuler']
                if any(word in message_lower for word in exit_words):
                    # Let normal detection handle these
                    pass
                else:
                    # Otherwise, treat as continuation of edit
                    print(f"[*] Context override: treating as EDIT (stage: {edit_stage})")
                    return Intent.EDIT
        
        # Regular keyword matching for non-context cases
        for intent, keywords in IntentDetector.INTENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in message_lower:
                    print(f"[+] Intent detected: {intent.value} (keyword: '{keyword}')")
                    return intent
        
        # Default to UNCLEAR if no keywords match
        print(f"[?] Intent unclear for: '{message}'")
        return Intent.UNCLEAR
    
    @staticmethod
    def requires_llm(intent: Intent) -> bool:
        """
        Determine if this intent requires LLM processing
        
        MCP Server uses this to decide when to call the LLM
        """
        llm_required = {
            Intent.BOOK,
            Intent.EDIT,
            Intent.CANCEL,
            Intent.VIEW,
            Intent.UNCLEAR
        }
        
        return intent in llm_required
    
    @staticmethod
    def requires_tools(intent: Intent) -> bool:
        """
        Determine if this intent requires tool/service calls
        
        MCP Server uses this to decide when to call business logic
        """
        # These intents need to interact with calendar service
        tools_required = {
            Intent.BOOK,
            Intent.EDIT,
            Intent.CANCEL,
            Intent.VIEW
        }
        
        return intent in tools_required

print("[+] Intent detection module loaded (FIXED: Context-Aware)")