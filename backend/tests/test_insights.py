"""Tests for Insights dashboards + volunteer profile endpoint (iteration 5)."""
import os
import requests
import pytest

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")


def _login(username, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"username": username, "password": password}, timeout=20)
    assert r.status_code == 200, r.text
    return s


# ---- /api/insights/organizer ----

def test_insights_organizer_unauth():
    r = requests.get(f"{BASE_URL}/api/insights/organizer", timeout=20)
    assert r.status_code == 401


def test_insights_organizer_forbidden_for_volunteer():
    s = _login("maya", "maya1234")
    r = s.get(f"{BASE_URL}/api/insights/organizer", timeout=20)
    assert r.status_code == 403


def test_insights_organizer_success_shape():
    s = _login("campusadmin", "admin1234")
    r = s.get(f"{BASE_URL}/api/insights/organizer", timeout=20)
    assert r.status_code == 200
    data = r.json()
    for key in ("total_events","events_open","events_completed","total_volunteers","total_hours","pending_applications","skill_coverage","top_volunteers","event_summary"):
        assert key in data, f"missing {key}"
    assert isinstance(data["skill_coverage"], list)
    assert isinstance(data["top_volunteers"], list)
    assert len(data["top_volunteers"]) <= 5
    # top_volunteers sorted desc by hours
    hours = [v["hours"] for v in data["top_volunteers"]]
    assert hours == sorted(hours, reverse=True)
    for v in data["top_volunteers"]:
        for k in ("username","name","department","hours"):
            assert k in v
    for sc in data["skill_coverage"]:
        for k in ("skill","required_in_events","available_volunteers"):
            assert k in sc
    for e in data["event_summary"]:
        for k in ("id","title","date","status","accepted","completed","pending","capacity"):
            assert k in e


# ---- /api/insights/volunteer ----

def test_insights_volunteer_unauth():
    r = requests.get(f"{BASE_URL}/api/insights/volunteer", timeout=20)
    assert r.status_code == 401


def test_insights_volunteer_forbidden_for_organizer():
    s = _login("campusadmin", "admin1234")
    r = s.get(f"{BASE_URL}/api/insights/volunteer", timeout=20)
    assert r.status_code == 403


def test_insights_volunteer_success_shape():
    s = _login("maya", "maya1234")
    r = s.get(f"{BASE_URL}/api/insights/volunteer", timeout=20)
    assert r.status_code == 200
    data = r.json()
    for key in ("events_applied","events_pending","events_accepted","events_completed","total_hours","certificates_earned","skills","department","matching_opportunities","events_by_status"):
        assert key in data, f"missing {key}"
    ebs = data["events_by_status"]
    for k in ("pending","accepted","completed"):
        assert k in ebs and isinstance(ebs[k], list)
    assert data["events_completed"] == len(ebs["completed"])
    assert data["events_pending"] == len(ebs["pending"])
    assert data["events_accepted"] == len(ebs["accepted"])


# ---- /api/users/{username} ----

def test_user_profile_self_volunteer():
    s = _login("maya", "maya1234")
    r = s.get(f"{BASE_URL}/api/users/maya", timeout=20)
    assert r.status_code == 200
    data = r.json()
    assert data["username"] == "maya"
    for k in ("name","department","role","skills","events_completed","total_hours","certificates_earned","completed_events"):
        assert k in data
    assert isinstance(data["completed_events"], list)


def test_user_profile_404():
    s = _login("campusadmin", "admin1234")
    r = s.get(f"{BASE_URL}/api/users/doesnotexist_xyz", timeout=20)
    assert r.status_code == 404


def test_user_profile_organizer_views_applicant():
    s = _login("campusadmin", "admin1234")
    # maya has applied to seeded organizer events - should be allowed
    r = s.get(f"{BASE_URL}/api/users/maya", timeout=20)
    assert r.status_code == 200, r.text
    assert r.json()["username"] == "maya"


def test_user_profile_unauth():
    r = requests.get(f"{BASE_URL}/api/users/maya", timeout=20)
    assert r.status_code == 401


def test_user_profile_volunteer_cannot_view_other():
    # maya trying to view campusadmin or another user
    s = _login("maya", "maya1234")
    r = s.get(f"{BASE_URL}/api/users/campusadmin", timeout=20)
    # volunteer accessing another user -> 403 by rule
    assert r.status_code in (403, 404)
