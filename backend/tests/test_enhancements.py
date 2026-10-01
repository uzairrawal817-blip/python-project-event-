"""Backend tests for 4 SkillMatch enhancements: PDF cert, event edit/delete, profile edit, QR check-in."""
import os
import uuid
import requests
import pytest

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")


def _login(session, username, password):
    r = session.post(f"{BASE_URL}/api/auth/login", json={"username": username, "password": password}, timeout=20)
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture
def volunteer_session():
    s = requests.Session()
    _login(s, "maya", "maya1234")
    return s


@pytest.fixture
def organizer_session():
    s = requests.Session()
    _login(s, "campusadmin", "admin1234")
    return s


# ---- Enhancement 3: Profile editing ----
class TestProfileEdit:
    def test_patch_me_updates_profile(self, volunteer_session):
        orig = volunteer_session.get(f"{BASE_URL}/api/auth/me", timeout=20).json()
        new_name = f"Maya TEST {uuid.uuid4().hex[:4]}"
        r = volunteer_session.patch(
            f"{BASE_URL}/api/auth/me",
            json={"name": new_name, "department": "Information Technology", "skills": ["Python", "Testing"]},
            timeout=20,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["name"] == new_name
        assert body["department"] == "Information Technology"
        assert "Testing" in body["skills"]

        got = volunteer_session.get(f"{BASE_URL}/api/auth/me", timeout=20).json()
        assert got["name"] == new_name
        assert got["department"] == "Information Technology"

        # restore
        volunteer_session.patch(
            f"{BASE_URL}/api/auth/me",
            json={"name": orig["name"], "department": orig["department"], "skills": orig["skills"]},
            timeout=20,
        )

    def test_patch_me_unauthenticated(self):
        r = requests.patch(f"{BASE_URL}/api/auth/me", json={"name": "x", "department": "y", "skills": []}, timeout=20)
        assert r.status_code == 401


# ---- Enhancement 2: Event edit/delete + checkin_code visibility ----
class TestEventEditDelete:
    def test_create_edit_delete_and_ownership(self, organizer_session, volunteer_session):
        payload = {"title": "TEST Edit Event", "description": "Original description for test.",
                   "date": "2026-05-01", "time": "09:00 AM", "location": "TEST Hall",
                   "required_skills": ["Teamwork"], "capacity": 10}
        c = organizer_session.post(f"{BASE_URL}/api/events", json=payload, timeout=20)
        assert c.status_code == 200
        ev = c.json()
        eid = ev["id"]
        # Organizer sees checkin_code for own event
        assert "checkin_code" in ev and len(ev["checkin_code"]) >= 4

        # Volunteer should NOT see checkin_code
        v_events = volunteer_session.get(f"{BASE_URL}/api/events", timeout=20).json()
        v_match = next((e for e in v_events if e["id"] == eid), None)
        assert v_match is not None
        assert "checkin_code" not in v_match, "checkin_code must not be exposed to volunteers"

        # PATCH update
        upd = payload | {"title": "TEST Edit Event UPDATED", "capacity": 15}
        pr = organizer_session.patch(f"{BASE_URL}/api/events/{eid}", json=upd, timeout=20)
        assert pr.status_code == 200, pr.text
        assert pr.json()["title"] == "TEST Edit Event UPDATED"
        assert pr.json()["capacity"] == 15

        # Volunteer cannot edit
        vpr = volunteer_session.patch(f"{BASE_URL}/api/events/{eid}", json=upd, timeout=20)
        assert vpr.status_code == 403

        # Volunteer cannot delete
        vdr = volunteer_session.delete(f"{BASE_URL}/api/events/{eid}", timeout=20)
        assert vdr.status_code == 403

        # Non-existent 404
        nf = organizer_session.patch(f"{BASE_URL}/api/events/nope-{uuid.uuid4().hex[:6]}", json=upd, timeout=20)
        assert nf.status_code == 404

        # Delete
        dr = organizer_session.delete(f"{BASE_URL}/api/events/{eid}", timeout=20)
        assert dr.status_code == 200
        # Non-existent delete 404
        nf2 = organizer_session.delete(f"{BASE_URL}/api/events/{eid}", timeout=20)
        assert nf2.status_code == 404


# ---- Enhancement 4: QR check-in ----
class TestCheckin:
    def test_full_checkin_flow_and_cert_pdf(self, organizer_session):
        # Create fresh event
        payload = {"title": "TEST QR Event", "description": "Check-in flow coverage test event.",
                   "date": "2026-06-01", "time": "10:00 AM", "location": "TEST Field",
                   "required_skills": [], "capacity": 10}
        c = organizer_session.post(f"{BASE_URL}/api/events", json=payload, timeout=20).json()
        eid = c["id"]
        code = c["checkin_code"]

        # Volunteer login via different session
        v = requests.Session()
        _login(v, "maya", "maya1234")

        # Not accepted yet -> checkin should be 409 (even with right code)
        r_not_joined = v.post(f"{BASE_URL}/api/events/{eid}/checkin", json={"code": code}, timeout=20)
        assert r_not_joined.status_code == 409

        # Apply
        ar = v.post(f"{BASE_URL}/api/events/{eid}/apply", timeout=20)
        assert ar.status_code == 200

        # Pending status, still 409
        r_pending = v.post(f"{BASE_URL}/api/events/{eid}/checkin", json={"code": code}, timeout=20)
        assert r_pending.status_code == 409

        # Organizer accepts
        ac = organizer_session.patch(
            f"{BASE_URL}/api/applications/{eid}/maya", json={"status": "accepted"}, timeout=20
        )
        assert ac.status_code == 200

        # Wrong code -> 400
        wrong = v.post(f"{BASE_URL}/api/events/{eid}/checkin", json={"code": "WRONG1"}, timeout=20)
        assert wrong.status_code == 400

        # Correct code -> 200
        ok = v.post(f"{BASE_URL}/api/events/{eid}/checkin", json={"code": code}, timeout=20)
        assert ok.status_code == 200
        assert ok.json()["ok"] is True

        # Cert endpoint returns PDF
        cert = v.get(f"{BASE_URL}/api/certificates/{eid}", timeout=20)
        assert cert.status_code == 200
        assert cert.headers.get("content-type", "").startswith("application/pdf")
        assert cert.content.startswith(b"%PDF")
        assert len(cert.content) > 1000
        assert "attachment" in cert.headers.get("content-disposition", "").lower()

        # Second checkin -> idempotent
        again = v.post(f"{BASE_URL}/api/events/{eid}/checkin", json={"code": code}, timeout=20)
        assert again.status_code == 200

        # Cleanup
        organizer_session.delete(f"{BASE_URL}/api/events/{eid}", timeout=20)


# ---- Enhancement 1: Cert PDF 404 for non-completed ----
class TestCertificatePdf:
    def test_cert_404_for_non_completed(self, volunteer_session):
        # event-fest - maya may or may not be applied, but shouldn't be completed
        r = volunteer_session.get(f"{BASE_URL}/api/certificates/event-fest", timeout=20)
        assert r.status_code == 404

    def test_cert_404_for_unknown_event(self, volunteer_session):
        r = volunteer_session.get(f"{BASE_URL}/api/certificates/does-not-exist-xyz", timeout=20)
        assert r.status_code == 404
