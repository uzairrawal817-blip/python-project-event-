import os
import requests

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")


def test_health_and_volunteer_auth_events_apply_certificate_flow():
    session = requests.Session()
    health = session.get(f"{BASE_URL}/api/health", timeout=20)
    assert health.status_code == 200 and health.json()["ok"] is True
    login = session.post(f"{BASE_URL}/api/auth/login", json={"username": "maya", "password": "maya1234"}, timeout=20)
    assert login.status_code == 200
    assert "skillmatch_token" in session.cookies and login.json()["role"] == "volunteer"
    assert session.get(f"{BASE_URL}/api/auth/me", timeout=20).json()["username"] == "maya"
    events = session.get(f"{BASE_URL}/api/events", timeout=20)
    assert events.status_code == 200 and len(events.json()) >= 3
    target = next(e for e in events.json() if e["id"] == "event-fest")
    if target["application"] is None:
        apply = session.post(f"{BASE_URL}/api/events/{target['id']}/apply", timeout=20)
        assert apply.status_code == 200 and apply.json()["ok"] is True
    assert session.get(f"{BASE_URL}/api/certificates", timeout=20).status_code == 200
    cert = session.get(f"{BASE_URL}/api/certificates/event-python", timeout=20)
    # Seeded application is accepted, not completed; this endpoint should correctly report not ready.
    assert cert.status_code == 404


def test_organizer_create_manage_and_complete_flow():
    session = requests.Session()
    login = session.post(f"{BASE_URL}/api/auth/login", json={"username": "campusadmin", "password": "admin1234"}, timeout=20)
    assert login.status_code == 200 and login.json()["role"] == "organizer"
    payload = {"title": "TEST Campus Cleanup", "description": "A test event for API regression coverage.", "date": "2025-12-01", "time": "10:00 AM", "location": "TEST Quad", "required_skills": ["Teamwork"], "capacity": 5}
    created = session.post(f"{BASE_URL}/api/events", json=payload, timeout=20)
    assert created.status_code == 200 and created.json()["title"] == payload["title"]
    applicants = session.get(f"{BASE_URL}/api/organizer/applicants", timeout=20)
    assert applicants.status_code == 200 and isinstance(applicants.json(), list)
    complete = session.post(f"{BASE_URL}/api/events/event-python/complete", json={"username": "maya", "hours": 2, "notes": "test"}, timeout=20)
    assert complete.status_code == 200 and complete.json()["ok"] is True