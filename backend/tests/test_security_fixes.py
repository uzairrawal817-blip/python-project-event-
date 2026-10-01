"""Security fix verification: SEC-001 (JWT hardening) and SEC-002 (ownership checks)."""
import os
import time
import uuid
import requests
import jwt
import pytest

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"


def _login(username, password):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, f"login failed for {username}: {r.status_code} {r.text}"
    return s


# ---------- SEC-001: JWT Hardening ----------
class TestSEC001JWTHardening:
    def test_health_ok(self):
        r = requests.get(f"{API}/health")
        assert r.status_code == 200

    def test_login_and_me_work(self):
        s = _login("maya", "maya1234")
        r = s.get(f"{API}/auth/me")
        assert r.status_code == 200
        assert r.json()["username"] == "maya"

        s2 = _login("campusadmin", "admin1234")
        r2 = s2.get(f"{API}/auth/me")
        assert r2.status_code == 200
        assert r2.json()["username"] == "campusadmin"

    def test_old_hardcoded_secret_rejected(self):
        """Token forged with the old fallback secret must be rejected."""
        forged = jwt.encode(
            {"sub": "campusadmin", "exp": int(time.time()) + 3600},
            "skillmatch-school-demo-secret",
            algorithm="HS256",
        )
        r = requests.get(f"{API}/auth/me", cookies={"skillmatch_token": forged})
        assert r.status_code == 401, f"Expected 401, got {r.status_code}: {r.text}"


# ---------- SEC-002: Ownership checks ----------
@pytest.fixture(scope="module")
def two_orgs_and_event():
    suffix = uuid.uuid4().hex[:6]
    org_a_user = f"org_a_{suffix}"
    org_b_user = f"org_b_{suffix}"
    pw = "pass1234"

    for u in (org_a_user, org_b_user):
        r = requests.post(f"{API}/auth/register", json={
            "username": u, "password": pw, "name": f"Org {u}",
            "role": "organizer", "department": "CS", "skills": []
        })
        assert r.status_code in (200, 201), f"register {u}: {r.status_code} {r.text}"

    sa = _login(org_a_user, pw)
    sb = _login(org_b_user, pw)

    # Org A creates event
    ev_payload = {
        "title": "Sec Test Event",
        "description": "Testing ownership checks",
        "date": "2026-12-01",
        "time": "10:00",
        "location": "Hall A",
        "skills_needed": ["python"],
        "volunteers_needed": 3,
    }
    r = sa.post(f"{API}/events", json=ev_payload)
    assert r.status_code in (200, 201), f"create event: {r.status_code} {r.text}"
    event_id = r.json()["id"]

    # Maya applies
    sm = _login("maya", "maya1234")
    r = sm.post(f"{API}/events/{event_id}/apply")
    assert r.status_code in (200, 201), f"apply: {r.status_code} {r.text}"

    yield {"sa": sa, "sb": sb, "sm": sm, "event_id": event_id,
           "org_a": org_a_user, "org_b": org_b_user}


class TestSEC002Ownership:
    def test_org_b_cannot_accept(self, two_orgs_and_event):
        d = two_orgs_and_event
        r = d["sb"].patch(f"{API}/applications/{d['event_id']}/maya",
                          json={"status": "accepted"})
        assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text}"
        assert "your own events" in r.text.lower()

    def test_org_a_can_accept(self, two_orgs_and_event):
        d = two_orgs_and_event
        r = d["sa"].patch(f"{API}/applications/{d['event_id']}/maya",
                         json={"status": "accepted"})
        assert r.status_code == 200, f"org A accept failed: {r.status_code} {r.text}"

    def test_org_b_cannot_complete(self, two_orgs_and_event):
        d = two_orgs_and_event
        r = d["sb"].post(f"{API}/events/{d['event_id']}/complete")
        assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text}"
        assert "your own events" in r.text.lower()

    def test_org_a_can_complete(self, two_orgs_and_event):
        d = two_orgs_and_event
        r = d["sa"].post(f"{API}/events/{d['event_id']}/complete")
        assert r.status_code == 200, f"org A complete failed: {r.status_code} {r.text}"

    def test_patch_app_nonexistent_event_404(self, two_orgs_and_event):
        d = two_orgs_and_event
        r = d["sa"].patch(f"{API}/applications/nonexistent-event-id-xyz/maya",
                          json={"status": "accepted"})
        assert r.status_code == 404, f"expected 404, got {r.status_code}: {r.text}"

    def test_complete_nonexistent_event_404(self, two_orgs_and_event):
        d = two_orgs_and_event
        r = d["sa"].post(f"{API}/events/nonexistent-event-id-xyz/complete")
        assert r.status_code == 404, f"expected 404, got {r.status_code}: {r.text}"


# ---------- Regression ----------
class TestRegression:
    def test_logout(self):
        s = _login("maya", "maya1234")
        r = s.post(f"{API}/auth/logout")
        assert r.status_code == 200

    def test_event_crud_own(self):
        s = _login("campusadmin", "admin1234")
        payload = {
            "title": "Regression Event", "description": "regression testing event",
            "date": "2026-11-15", "time": "14:00", "location": "Room 1",
            "skills_needed": ["java"], "volunteers_needed": 2,
        }
        r = s.post(f"{API}/events", json=payload)
        assert r.status_code in (200, 201), r.text
        eid = r.json()["id"]

        r = s.put(f"{API}/events/{eid}", json={**payload, "title": "Regression Event v2"})
        assert r.status_code == 200, r.text

        r = s.delete(f"{API}/events/{eid}")
        assert r.status_code == 200, r.text

    def test_insights_endpoints(self):
        so = _login("campusadmin", "admin1234")
        r = so.get(f"{API}/insights/organizer")
        assert r.status_code == 200

        sv = _login("maya", "maya1234")
        r = sv.get(f"{API}/insights/volunteer")
        assert r.status_code == 200

    def test_volunteer_profile_view(self):
        s = _login("campusadmin", "admin1234")
        r = s.get(f"{API}/users/maya")
        assert r.status_code == 200
        assert r.json()["username"] == "maya"
