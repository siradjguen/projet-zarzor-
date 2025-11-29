// src/components/MedicalChatbot.jsx - Medical Chatbot (No Voice)

import React, { useState, useEffect, useRef } from 'react';
import './MedicalChatbot.css';

const API_URL = 'http://localhost:8000/api/chat';

const MedicalChatbot = () => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId] = useState(() => `session_${Date.now()}`);
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Welcome message
  useEffect(() => {
    setMessages([
      {
        role: 'assistant',
        content: "👋 Hello! I'm Dr. AI, your medical appointment assistant.\n\nI can help you with:\n\n🗓️ Book new appointments\n✏️ Modify existing appointments\n❌ Cancel appointments\n💬 Answer questions about our clinic\n\nHow may I assist you today?",
        timestamp: new Date().toISOString()
      }
    ]);
  }, []);

  // Send message to backend
  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage = {
      role: 'user',
      content: inputMessage,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: inputMessage,
          session_id: sessionId
        })
      });

      const data = await response.json();

      if (data.success) {
        const aiMessage = {
          role: 'assistant',
          content: data.message,
          timestamp: data.timestamp,
          metadata: data.metadata
        };
        setMessages(prev => [...prev, aiMessage]);
      } else {
        throw new Error(data.error || 'Failed to get response');
      }

    } catch (error) {
      console.error('Error:', error);
      const errorMessage = {
        role: 'assistant',
        content: '❌ Sorry, I encountered an error. Please try again or call us at +1-555-MEDICAL.',
        timestamp: new Date().toISOString(),
        isError: true
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle Enter key
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // Clear conversation
  const clearChat = async () => {
    if (!window.confirm('Clear this conversation?')) return;

    try {
      await fetch(`http://localhost:8000/api/conversation/${sessionId}`, {
        method: 'DELETE'
      });
      
      setMessages([
        {
          role: 'assistant',
          content: '🔄 Conversation cleared. How can I help you?',
          timestamp: new Date().toISOString()
        }
      ]);
    } catch (error) {
      console.error('Error clearing chat:', error);
    }
  };

  // Format timestamp
  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className="chatbot-wrapper">
      {/* Animated Medical Background */}
      <div className="medical-bg">
        <div className="floating-cross cross-1">+</div>
        <div className="floating-cross cross-2">+</div>
        <div className="floating-cross cross-3">+</div>
        <div className="floating-heart">❤️</div>
        <div className="floating-pill">💊</div>
      </div>

      <div className="chatbot-container">
        {/* Header */}
        <div className="chatbot-header">
          <div className="header-icon">
            <div className="pulse-ring"></div>
            <div className="doctor-icon">👨‍⚕️</div>
          </div>
          <div className="header-content">
            <h1>Dr. AI Medical Assistant</h1>
            <p className="status-online">
              <span className="status-dot"></span>
              Online • Ready to Help
            </p>
          </div>
          <button onClick={clearChat} className="clear-btn" title="Clear conversation">
            <span>🗑️</span>
          </button>
        </div>

        {/* Messages Area */}
        <div className="messages-container">
          {messages.map((msg, index) => (
            <div
              key={index}
              className={`message ${msg.role} ${msg.isError ? 'error' : ''}`}
            >
              <div className="message-avatar">
                <div className="avatar-ring"></div>
                {msg.role === 'user' ? '👤' : '🤖'}
              </div>
              <div className="message-bubble">
                <div className="message-text">
                  {msg.content.split('\n').map((line, i) => (
                    <p key={i}>{line || '\u00A0'}</p>
                  ))}
                </div>
                <div className="message-footer">
                  <span className="message-time">
                    {formatTime(msg.timestamp)}
                  </span>
                  {msg.metadata && (
                    <span className="message-info">
                      ⚡ {msg.metadata.duration}s • 🔢 {msg.metadata.tokens_used}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}

          {/* Loading indicator */}
          {isLoading && (
            <div className="message assistant loading">
              <div className="message-avatar">
                <div className="avatar-ring"></div>
                🤖
              </div>
              <div className="message-bubble">
                <div className="typing-indicator">
                  <div className="typing-dot"></div>
                  <div className="typing-dot"></div>
                  <div className="typing-dot"></div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="input-container">
          <div className="input-wrapper">
            <textarea
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your message here..."
              disabled={isLoading}
              rows="1"
            />

            <button
              onClick={sendMessage}
              disabled={isLoading || !inputMessage.trim()}
              className="send-btn"
              title="Send message"
            >
              {isLoading ? '⏳' : '➤'}
            </button>
          </div>

          <div className="input-footer">
            <div className="footer-info">
              <span className="secure-badge">🔒 Secure & Private</span>
              <span className="powered-by">Powered by Groq AI • Free Forever</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MedicalChatbot;