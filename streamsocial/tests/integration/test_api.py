import requests

def test_user_registration():
    data = {"username": "testuser123", "email": "test@example.com"}
    response = requests.post("http://localhost:8000/events/user/register", json=data)
    assert response.status_code == 200
    assert response.json()["success"] is True