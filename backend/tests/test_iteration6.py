"""Iteration 6 regression tests: new event fields (duration/department/event_type),
seats_available calc, organizer ownership enforcement for applications & complete."""
import os
import pytest
import requests

def _load_backend_url():
    import pathlib
    env_file = pathlib.Path("/app/frontend/.env")
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip()
    return os.environ.get("REACT_APP_BACKEND_URL", "")

BASE_URL = _load_backend_url().rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL missing"
API = f"{BASE_URL}/api"


def login(username, password):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def organizer():
    return login("campusadmin", "admin1234")


@pytest.fixture(scope="module")
def volunteer():
    return login("maya", "maya1234")


def test_events_include_new_fields(volunteer):
    r = volunteer.get(f"{API}/events")
    assert r.status_code == 200
    events = r.json()
    assert len(events) >= 1
    for e in events:
        for k in ["duration", "department", "event_type", "organizer_name", "seats_available", "capacity"]:
            assert k in e, f"missing {k} in {e.get('id')}"
        # seats = capacity - accepted/completed volunteers
        assert e["seats_available"] == max(0, e["capacity"] - e["volunteers"])
        # checkin_code must NOT leak to volunteer
        assert "checkin_code" not in e


def test_organizer_sees_checkin_code_only_on_own(organizer):
    r = organizer.get(f"{API}/events")
    assert r.status_code == 200
    for e in r.json():
        if e["organizer"] == "campusadmin":
            assert "checkin_code" in e and len(e["checkin_code"]) >= 4


def test_create_event_with_new_fields(organizer):
    payload = {
        "title": "TEST_Iter6 Workshop",
        "description": "Testing new event fields duration department event_type.",
        "date": "2026-05-10",
        "time": "11:00 AM",
        "duration": "2 hours",
        "location": "Room 101",
        "department": "Computer Science",
        "event_type": "Learning",
        "required_skills": ["Python"],
        "capacity": 5,
    }
    r = organizer.post(f"{API}/events", json=payload)
    assert r.status_code == 200, r.text
    e = r.json()
    assert e["duration"] == "2 hours"
    assert e["department"] == "Computer Science"
    assert e["event_type"] == "Learning"
    assert e["organizer_name"] == "Campus Events Office"
    assert e["seats_available"] == 5
    # cleanup
    organizer.delete(f"{API}/events/{e['id']}")


def test_apply_decrements_seats_only_on_accept(organizer, volunteer):
    # create event
    r = organizer.post(f"{API}/events", json={
        "title": "TEST_Iter6 Seats", "description": "Seats-available decrement test flow.",
        "date": "2026-06-01", "time": "10:00 AM", "duration": "1 hour", "location": "Lab A",
        "department": "Student Life", "event_type": "Community",
        "required_skills": [], "capacity": 3,
    })
    eid = r.json()["id"]
    try:
        # volunteer applies
        ar = volunteer.post(f"{API}/events/{eid}/apply")
        assert ar.status_code == 200
        # fetch -> seats still 3 (pending)
        ev = next(e for e in volunteer.get(f"{API}/events").json() if e["id"] == eid)
        assert ev["seats_available"] == 3
        assert ev["application"] == "pending"
        # accept
        sr = organizer.patch(f"{API}/applications/{eid}/maya", json={"status": "accepted"})
        assert sr.status_code == 200
        ev = next(e for e in volunteer.get(f"{API}/events").json() if e["id"] == eid)
        assert ev["seats_available"] == 2
        assert ev["application"] == "accepted"
    finally:
        organizer.delete(f"{API}/events/{eid}")


def test_organizer_ownership_enforced(volunteer, organizer):
    # Create a second organizer
    reg = requests.post(f"{API}/auth/register", json={
        "username": "test_org_b", "password": "pass1234", "name": "Org B",
        "role": "organizer", "department": "Test", "skills": [],
    })
    assert reg.status_code in (200, 409)
    org_b = login("test_org_b", "pass1234")

    # org A creates event
    r = organizer.post(f"{API}/events", json={
        "title": "TEST_Iter6 Ownership", "description": "Test ownership enforcement for applications.",
        "date": "2026-07-01", "time": "10:00 AM", "duration": "1h", "location": "Lab X",
        "department": "Test", "event_type": "Learning",
        "required_skills": [], "capacity": 2,
    })
    assert r.status_code == 200, f"create failed {r.status_code} {r.text}"
    eid = r.json()["id"]
    try:
        volunteer.post(f"{API}/events/{eid}/apply")
        # org B tries to accept volunteer on org A's event -> 403
        r1 = org_b.patch(f"{API}/applications/{eid}/maya", json={"status": "accepted"})
        assert r1.status_code == 403, r1.text
        # org B tries to complete -> 403
        r2 = org_b.post(f"{API}/events/{eid}/complete", json={"username": "maya", "hours": 1, "notes": ""})
        assert r2.status_code == 403
        # missing event -> 404
        r3 = org_b.patch(f"{API}/applications/does-not-exist/maya", json={"status": "accepted"})
        assert r3.status_code == 404
        r4 = org_b.post(f"{API}/events/does-not-exist/complete", json={"username": "maya", "hours": 1, "notes": ""})
        assert r4.status_code == 404
    finally:
        organizer.delete(f"{API}/events/{eid}")


def test_derive_event_type_default():
    # ensure default event_type is one of the known buckets for seeded events
    s = login("maya", "maya1234")
    events = s.get(f"{API}/events").json()
    allowed = {"Learning", "Culture", "Community", "Sports", "Service"}
    for e in events:
        assert e["event_type"] in allowed, f"{e['id']}={e['event_type']}"
