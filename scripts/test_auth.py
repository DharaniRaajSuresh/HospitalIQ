import requests
import json

BASE_URL = "http://localhost:8000/api/v1/auth"

# 1. Try to register
resp = requests.post(f"{BASE_URL}/register", json={
    "email": "test@example.com",
    "password": "password",
    "full_name": "Test User"
})
print("Register:", resp.status_code, resp.text)

# 2. Try to register again
resp = requests.post(f"{BASE_URL}/register", json={
    "email": "test@example.com",
    "password": "password",
    "full_name": "Test User"
})
print("Register again:", resp.status_code, resp.text)

# 3. Try to login
resp = requests.post(f"{BASE_URL}/login", json={
    "email": "test@example.com",
    "password": "password"
})
print("Login:", resp.status_code, resp.text)
