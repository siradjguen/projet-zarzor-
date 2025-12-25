import requests
import json
import time
from typing import Dict

BASE_URL = "http://localhost:8000"
SESSION_ID = "test_session_001"

def chat(message: str) -> Dict:
    """Send a chat message and get response"""
    response = requests.post(
        f"{BASE_URL}/chat",
        json={
            "session_id": SESSION_ID,
            "message": message
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n{'='*60}")
        print(f"USER: {message}")
        print(f"ASSISTANT: {data['reply']}")
        print(f"{'='*60}")
        return data
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return {}

def test_conversation_flow():
    """Test a complete conversation flow"""
    
    print("\n🧪 TESTING MEDIBOOK CLINIC API")
    print("=" * 60)
    
    # Test 1: Greeting
    print("\n📝 TEST 1: Greeting")
    chat("Hello")
    time.sleep(1)
    
    # Test 2: Booking appointment
    print("\n📝 TEST 2: Book Appointment")
    chat("I want to book an appointment for Ahmed Benali, phone 0555123456, Monday at 2pm")
    time.sleep(2)
    
    # Test 3: View appointments
    print("\n📝 TEST 3: View Appointments")
    chat("Show my appointments for phone 0555123456")
    time.sleep(2)
    
    # Test 4: Book another appointment
    print("\n📝 TEST 4: Book Another Appointment")
    chat("Book for Sara Mansouri, 0666789012, Friday at 10am, consultation with Dr. Amrani")
    time.sleep(2)
    
    # Test 5: Help
    print("\n📝 TEST 5: Help Request")
    chat("What can you do?")
    time.sleep(1)
    
    # Test 6: Goodbye
    print("\n📝 TEST 6: Goodbye")
    chat("Thank you, goodbye")
    time.sleep(1)
    
    print("\n✅ All tests completed!")

def test_edge_cases():
    """Test edge cases and error handling"""
    
    print("\n🧪 TESTING EDGE CASES")
    print("=" * 60)
    
    # Test 1: Incomplete information
    print("\n📝 TEST: Incomplete Booking Info")
    chat("I want to book an appointment")
    time.sleep(1)
    
    # Test 2: Invalid date
    print("\n📝 TEST: Past Date")
    chat("Book for John Doe, phone 0555999888, yesterday at 10am")
    time.sleep(1)
    
    # Test 3: View non-existent appointments
    print("\n📝 TEST: Non-existent Appointments")
    chat("Show appointments for 0999999999")
    time.sleep(1)
    
    print("\n✅ Edge case tests completed!")

def test_health_check():
    """Test health check endpoint"""
    print("\n🏥 Testing Health Check...")
    response = requests.get(f"{BASE_URL}/health")
    
    if response.status_code == 200:
        print(f"✅ Health Check: {response.json()}")
    else:
        print(f"❌ Health Check Failed: {response.status_code}")

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════╗
║         MEDIBOOK CLINIC API TEST SUITE                   ║
║         MCP Architecture Demonstration                   ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    # Check if server is running
    try:
        test_health_check()
        print("\n" + "="*60)
        
        # Run tests
        test_conversation_flow()
        print("\n" + "="*60)
        test_edge_cases()
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Cannot connect to API server")
        print("Make sure the server is running with: python main.py")
        print(f"Expected URL: {BASE_URL}")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()