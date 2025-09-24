#!/usr/bin/env python
"""
Quick test script to check registration performance
"""
import os
import sys
import django
import time
import requests
import json
from datetime import datetime

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'driver_app_backend.settings')
django.setup()

def test_registration_endpoint():
    """Test the registration endpoint performance"""
    url = 'http://localhost:8000/api/v1/auth/register/'
    
    test_data = {
        'email': f'test{int(time.time())}@example.com',
        'phone_number': f'+1234567{int(time.time() % 10000):04d}',
        'full_name': 'Test User',
        'password': 'TestPassword123!',
        'confirm_password': 'TestPassword123!'
    }
    
    print(f"Testing registration endpoint at {datetime.now()}")
    print(f"Test data: {json.dumps(test_data, indent=2)}")
    print("-" * 50)
    
    start_time = time.time()
    
    try:
        response = requests.post(url, json=test_data, timeout=30)
        end_time = time.time()
        
        duration = end_time - start_time
        
        print(f"✅ Request completed in {duration:.3f} seconds")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        
        if duration < 1.0:
            print("🚀 EXCELLENT: Registration is very fast!")
        elif duration < 2.0:
            print("✅ GOOD: Registration is reasonably fast")
        elif duration < 5.0:
            print("⚠️  FAIR: Registration is acceptable but could be faster")
        else:
            print("❌ SLOW: Registration is too slow")
            
    except requests.exceptions.Timeout:
        print("❌ TIMEOUT: Request took longer than 30 seconds")
    except requests.exceptions.ConnectionError:
        print("❌ CONNECTION ERROR: Could not connect to the server")
        print("Make sure the Django server is running: python manage.py runserver")
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == '__main__':
    print("🧪 Registration Performance Test")
    print("=" * 50)
    test_registration_endpoint()