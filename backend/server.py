from dotenv import load_dotenv
load_dotenv()

import io
import os
import secrets
import string
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import bcrypt
import jwt
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import landscape, letter
from reportlab.pdfgen import canvas

ROOT_DIR = Path(__file__).parent
client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]
JWT_SECRET = os.environ.get("JWT_SECRET", "").strip()
if not JWT_SECRET or len(JWT_SECRET) < 32:
    raise RuntimeError("JWT_SECRET env var must be set to a strong value (>=32 chars). Refusing to start.")
JWT_ALGORITHM = "HS256"
app = FastAPI(title="SkillMatch API")
api = APIRouter(prefix="/api")


def gen_checkin_code() -> str:
    return "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))


class LoginInput(BaseModel):
    username: str = Field(min_length=2, max_length=40)
    password: str = Field(min_length=4, max_length=100)


class RegisterInput(LoginInput):
    name: str = Field(min_length=2, max_length=80)
    role: str = Field(pattern="^(organizer|volunteer)$")
    department: str = Field(min_length=2, max_length=80)
    skills: list[str] = []


class ProfileInput(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    department: str = Field(min_length=2, max_length=80)
    skills: list[str] = []


class EventInput(BaseModel):
    title: str = Field(min_length=3, max_length=100)
    description: str = Field(min_length=10, max_length=500)
    date: str
    time: str
    location: str = Field(min_length=2, max_length=100)
    required_skills: list[str] = []
    capacity: int = Field(ge=1, le=500)


class StatusInput(BaseModel):
    status: str = Field(pattern="^(accepted|rejected)$")


class CompleteInput(BaseModel):
    username: str
    hours: float = Field(ge=0, le=100)
    notes: str = Field(default="", max_length=300)


class CheckinInput(BaseModel):
    code: str = Field(min_length=4, max_length=12)


def public_user(user: dict) -> dict:
    return {
        "id": str(user.get("_id", user.get("id", user["username"]))),
        "username": user["username"],
        "name": user["name"],
        "role": user["role"],
        "department": user.get("department", ""),
        "skills": user.get("skills", []),
    }


def token_for(user: dict) -> str:
    return jwt.encode(
        {"sub": user["username"], "exp": datetime.now(timezone.utc).timestamp() + 86400},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


async def current_user(request: Request) -> dict:
    token = request.cookies.get("skillmatch_token") or request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        raise HTTPException(401, "Please sign in to continue")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user = await db.users.find_one({"username": payload["sub"]}, {"_id": 0})
        if not user:
            raise HTTPException(401, "Your session is no longer active")
        return user
    except jwt.PyJWTError:
        raise HTTPException(401, "Your session has expired")


async def seed_data():
    if await db.users.count_documents({}) == 0:
        await db.users.insert_many([
            {"username": "maya", "password_hash": bcrypt.hashpw(b"maya1234", bcrypt.gensalt()).decode(), "name": "Maya Singh", "role": "volunteer", "department": "Computer Science", "skills": ["Python", "Design", "Public speaking"]},
            {"username": "campusadmin", "password_hash": bcrypt.hashpw(b"admin1234", bcrypt.gensalt()).decode(), "name": "Campus Events Office", "role": "organizer", "department": "Student Life", "skills": []},
        ])
    if await db.events.count_documents({}) == 0:
        await db.events.insert_many([
            {"id": "event-python", "title": "Python for Everyone", "description": "A welcoming hands-on workshop helping first-years build their first useful script.", "date": "2026-03-18", "time": "10:00 AM", "location": "Innovation Lab · Block C", "required_skills": ["Python", "Public speaking"], "capacity": 12, "organizer": "campusadmin", "status": "open", "checkin_code": gen_checkin_code()},
            {"id": "event-fest", "title": "Founders Day Festival", "description": "Make the annual campus celebration unforgettable for 2,000 students.", "date": "2026-03-21", "time": "04:30 PM", "location": "Central Quad", "required_skills": ["Design", "Event planning"], "capacity": 30, "organizer": "campusadmin", "status": "open", "checkin_code": gen_checkin_code()},
            {"id": "event-green", "title": "Green Campus Drive", "description": "A morning of planting, cleanup, and small actions with a big campus impact.", "date": "2026-03-27", "time": "08:30 AM", "location": "North Garden", "required_skills": ["Teamwork"], "capacity": 25, "organizer": "campusadmin", "status": "open", "checkin_code": gen_checkin_code()},
        ])
    # Backfill checkin_code for any legacy events
    async for e in db.events.find({"checkin_code": {"$exists": False}}, {"_id": 0, "id": 1}):
        await db.events.update_one({"id": e["id"]}, {"$set": {"checkin_code": gen_checkin_code()}})
    if await db.applications.count_documents({}) == 0:
        await db.applications.insert_one({"event_id": "event-python", "username": "maya", "status": "accepted", "hours": 0, "notes": ""})


@app.on_event("startup")
async def startup():
    await seed_data()


@api.get("/health")
async def health():
    return {"ok": True, "service": "SkillMatch"}


@api.post("/auth/login")
async def login(data: LoginInput, response: Response):
    user = await db.users.find_one({"username": data.username.strip().lower()}, {"_id": 0})
    if not user or not bcrypt.checkpw(data.password.encode(), user["password_hash"].encode()):
        raise HTTPException(401, "That username or password is not right")
    response.set_cookie("skillmatch_token", token_for(user), httponly=True, samesite="lax", max_age=86400)
    return public_user(user)


@api.post("/auth/register")
async def register(data: RegisterInput, response: Response):
    username = data.username.strip().lower()
    if await db.users.find_one({"username": username}):
        raise HTTPException(409, "That username is already taken")
    user = {"username": username, "password_hash": bcrypt.hashpw(data.password.encode(), bcrypt.gensalt()).decode(), "name": data.name.strip(), "role": data.role, "department": data.department.strip(), "skills": data.skills}
    await db.users.insert_one(user)
    response.set_cookie("skillmatch_token", token_for(user), httponly=True, samesite="lax", max_age=86400)
    return public_user(user)


@api.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("skillmatch_token")
    return {"ok": True}


@api.get("/auth/me")
async def me(user: dict = Depends(current_user)):
    return public_user(user)


@api.patch("/auth/me")
async def update_profile(data: ProfileInput, user: dict = Depends(current_user)):
    await db.users.update_one(
        {"username": user["username"]},
        {"$set": {"name": data.name.strip(), "department": data.department.strip(), "skills": [s.strip() for s in data.skills if s.strip()]}},
    )
    fresh = await db.users.find_one({"username": user["username"]}, {"_id": 0})
    return public_user(fresh)


async def event_payload(event: dict, user: Optional[dict] = None) -> dict:
    result = {k: event.get(k) for k in ["id", "title", "description", "date", "time", "location", "required_skills", "capacity", "organizer", "status"]}
    apps = await db.applications.find({"event_id": event["id"]}, {"_id": 0}).to_list(100)
    result["volunteers"] = len([a for a in apps if a.get("status") in ["accepted", "completed"]])
    result["application"] = next((a.get("status") for a in apps if user and a.get("username") == user.get("username")), None)
    required = [s.lower() for s in event.get("required_skills", [])]
    user_skills = [s.lower() for s in (user.get("skills", []) if user else [])]
    result["match"] = bool(user and user.get("role") == "volunteer" and (not required or set(required) & set(user_skills)))
    # Only expose checkin_code to the organizer who owns the event
    if user and user.get("role") == "organizer" and event.get("organizer") == user.get("username"):
        result["checkin_code"] = event.get("checkin_code")
    return result


@api.get("/events")
async def events(user: dict = Depends(current_user)):
    return [await event_payload(e, user) for e in await db.events.find({}, {"_id": 0}).sort("date", 1).to_list(100)]


@api.post("/events")
async def create_event(data: EventInput, user: dict = Depends(current_user)):
    if user["role"] != "organizer":
        raise HTTPException(403, "Only organizers can create events")
    event = data.model_dump() | {"id": "event-" + secrets.token_hex(4), "organizer": user["username"], "status": "open", "checkin_code": gen_checkin_code()}
    await db.events.insert_one(event)
    return await event_payload(event, user)


@api.patch("/events/{event_id}")
async def update_event(event_id: str, data: EventInput, user: dict = Depends(current_user)):
    if user["role"] != "organizer":
        raise HTTPException(403, "Only organizers can edit events")
    event = await db.events.find_one({"id": event_id}, {"_id": 0})
    if not event:
        raise HTTPException(404, "Event not found")
    if event.get("organizer") != user["username"]:
        raise HTTPException(403, "You can only edit your own events")
    await db.events.update_one({"id": event_id}, {"$set": data.model_dump()})
    fresh = await db.events.find_one({"id": event_id}, {"_id": 0})
    return await event_payload(fresh, user)


@api.delete("/events/{event_id}")
async def delete_event(event_id: str, user: dict = Depends(current_user)):
    if user["role"] != "organizer":
        raise HTTPException(403, "Only organizers can delete events")
    event = await db.events.find_one({"id": event_id}, {"_id": 0})
    if not event:
        raise HTTPException(404, "Event not found")
    if event.get("organizer") != user["username"]:
        raise HTTPException(403, "You can only delete your own events")
    await db.events.delete_one({"id": event_id})
    await db.applications.delete_many({"event_id": event_id})
    return {"ok": True}


@api.post("/events/{event_id}/apply")
async def apply(event_id: str, user: dict = Depends(current_user)):
    if user["role"] != "volunteer":
        raise HTTPException(403, "Switch to volunteer mode to join an event")
    event = await db.events.find_one({"id": event_id}, {"_id": 0})
    if not event:
        raise HTTPException(404, "Event not found")
    if await db.applications.find_one({"event_id": event_id, "username": user["username"]}):
        raise HTTPException(409, "You already joined this event")
    await db.applications.insert_one({"event_id": event_id, "username": user["username"], "status": "pending", "hours": 0, "notes": ""})
    return {"ok": True}


@api.post("/events/{event_id}/checkin")
async def checkin(event_id: str, data: CheckinInput, user: dict = Depends(current_user)):
    if user["role"] != "volunteer":
        raise HTTPException(403, "Only volunteers can check in")
    event = await db.events.find_one({"id": event_id}, {"_id": 0})
    if not event:
        raise HTTPException(404, "Event not found")
    if event.get("checkin_code", "").upper() != data.code.strip().upper():
        raise HTTPException(400, "That check-in code does not match")
    row = await db.applications.find_one({"event_id": event_id, "username": user["username"]}, {"_id": 0})
    if not row:
        raise HTTPException(409, "Join this event before checking in")
    if row.get("status") == "completed":
        return {"ok": True, "already": True}
    if row.get("status") != "accepted":
        raise HTTPException(409, "Your organizer needs to accept you before check-in")
    await db.applications.update_one(
        {"event_id": event_id, "username": user["username"]},
        {"$set": {"status": "completed", "hours": row.get("hours") or 3, "notes": row.get("notes") or "Checked in on event day"}},
    )
    return {"ok": True}


@api.get("/organizer/applicants")
async def applicants(user: dict = Depends(current_user)):
    if user["role"] != "organizer":
        raise HTTPException(403, "Organizer access required")
    own = [e["id"] for e in await db.events.find({"organizer": user["username"]}, {"_id": 0, "id": 1}).to_list(100)]
    rows = []
    for app_row in await db.applications.find({"event_id": {"$in": own}}, {"_id": 0}).to_list(200):
        volunteer = await db.users.find_one({"username": app_row["username"]}, {"_id": 0})
        event = await db.events.find_one({"id": app_row["event_id"]}, {"_id": 0})
        rows.append({**app_row, "name": volunteer.get("name", app_row["username"]) if volunteer else app_row["username"], "skills": volunteer.get("skills", []) if volunteer else [], "event_title": event.get("title", "Event") if event else "Event"})
    return rows


@api.get("/insights/organizer")
async def organizer_insights(user: dict = Depends(current_user)):
    if user["role"] != "organizer":
        raise HTTPException(403, "Organizer access required")
    events = await db.events.find({"organizer": user["username"]}, {"_id": 0}).to_list(200)
    event_ids = [e["id"] for e in events]
    apps = await db.applications.find({"event_id": {"$in": event_ids}}, {"_id": 0}).to_list(500)

    total_hours = sum((a.get("hours") or 0) for a in apps if a.get("status") == "completed")
    unique_volunteers = {a["username"] for a in apps if a.get("status") in ["accepted", "completed"]}

    # Skill coverage: required skills across events vs covered by accepted/completed volunteers
    required_skills: dict[str, int] = {}
    for e in events:
        for s in e.get("required_skills", []):
            required_skills[s] = required_skills.get(s, 0) + 1
    covered_skills: dict[str, int] = {}
    for a in apps:
        if a.get("status") not in ["accepted", "completed"]:
            continue
        vol = await db.users.find_one({"username": a["username"]}, {"_id": 0, "skills": 1})
        for s in (vol or {}).get("skills", []):
            covered_skills[s] = covered_skills.get(s, 0) + 1
    skill_coverage = [
        {"skill": s, "required_in_events": required_skills[s], "available_volunteers": covered_skills.get(s, 0)}
        for s in sorted(required_skills.keys())
    ]

    # Top volunteers by hours
    hours_by_user: dict[str, float] = {}
    for a in apps:
        if a.get("status") == "completed":
            hours_by_user[a["username"]] = hours_by_user.get(a["username"], 0) + (a.get("hours") or 0)
    top_volunteers = []
    for username, hours in sorted(hours_by_user.items(), key=lambda kv: kv[1], reverse=True)[:5]:
        vol = await db.users.find_one({"username": username}, {"_id": 0})
        if vol:
            top_volunteers.append({"username": username, "name": vol.get("name", username), "department": vol.get("department", ""), "hours": hours})

    # Per-event summary
    event_summary = []
    for e in events:
        e_apps = [a for a in apps if a["event_id"] == e["id"]]
        event_summary.append({
            "id": e["id"],
            "title": e["title"],
            "date": e.get("date", ""),
            "status": e.get("status", "open"),
            "accepted": len([a for a in e_apps if a.get("status") == "accepted"]),
            "completed": len([a for a in e_apps if a.get("status") == "completed"]),
            "pending": len([a for a in e_apps if a.get("status") == "pending"]),
            "capacity": e.get("capacity", 0),
        })

    return {
        "total_events": len(events),
        "events_open": len([e for e in events if e.get("status") == "open"]),
        "events_completed": len([e for e in events if e.get("status") == "completed"]),
        "total_volunteers": len(unique_volunteers),
        "total_hours": total_hours,
        "pending_applications": len([a for a in apps if a.get("status") == "pending"]),
        "skill_coverage": skill_coverage,
        "top_volunteers": top_volunteers,
        "event_summary": event_summary,
    }


@api.get("/insights/volunteer")
async def volunteer_insights(user: dict = Depends(current_user)):
    if user["role"] != "volunteer":
        raise HTTPException(403, "Volunteer access required")
    my_apps = await db.applications.find({"username": user["username"]}, {"_id": 0}).to_list(200)
    total_hours = sum((a.get("hours") or 0) for a in my_apps if a.get("status") == "completed")
    completed = [a for a in my_apps if a.get("status") == "completed"]

    # Breakdown events
    events_by_status = {"pending": [], "accepted": [], "completed": []}
    for a in my_apps:
        event = await db.events.find_one({"id": a["event_id"]}, {"_id": 0})
        if not event or a.get("status") not in events_by_status:
            continue
        events_by_status[a["status"]].append({
            "id": event["id"],
            "title": event["title"],
            "date": event.get("date", ""),
            "location": event.get("location", ""),
            "hours": a.get("hours", 0),
        })

    # Skill match: how many events needed each of my skills
    my_skills = [s.lower() for s in user.get("skills", [])]
    events_matched = 0
    all_events = await db.events.find({}, {"_id": 0, "required_skills": 1}).to_list(500)
    for e in all_events:
        req = [s.lower() for s in e.get("required_skills", [])]
        if req and set(req) & set(my_skills):
            events_matched += 1

    return {
        "events_applied": len(my_apps),
        "events_pending": len(events_by_status["pending"]),
        "events_accepted": len(events_by_status["accepted"]),
        "events_completed": len(completed),
        "total_hours": total_hours,
        "certificates_earned": len(completed),
        "skills": user.get("skills", []),
        "department": user.get("department", ""),
        "matching_opportunities": events_matched,
        "events_by_status": events_by_status,
    }


@api.get("/users/{username}")
async def user_profile(username: str, user: dict = Depends(current_user)):
    target = await db.users.find_one({"username": username.lower()}, {"_id": 0})
    if not target:
        raise HTTPException(404, "That volunteer could not be found")
    # Only self or organizers who ran events the user applied to can view
    if user["username"] != target["username"] and user["role"] != "organizer":
        raise HTTPException(403, "You do not have access to this profile")
    if user["role"] == "organizer" and user["username"] != target["username"]:
        own = [e["id"] for e in await db.events.find({"organizer": user["username"]}, {"_id": 0, "id": 1}).to_list(100)]
        has_overlap = await db.applications.find_one({"username": target["username"], "event_id": {"$in": own}})
        if not has_overlap:
            raise HTTPException(403, "You can only view volunteers that applied to your events")

    apps = await db.applications.find({"username": target["username"]}, {"_id": 0}).to_list(200)
    completed = []
    for a in apps:
        if a.get("status") != "completed":
            continue
        event = await db.events.find_one({"id": a["event_id"]}, {"_id": 0})
        if not event:
            continue
        completed.append({
            "event_id": event["id"],
            "title": event["title"],
            "date": event.get("date", ""),
            "location": event.get("location", ""),
            "hours": a.get("hours", 0),
            "notes": a.get("notes", ""),
        })

    total_hours = sum((c.get("hours") or 0) for c in completed)
    return {
        "username": target["username"],
        "name": target.get("name", target["username"]),
        "department": target.get("department", ""),
        "role": target.get("role", "volunteer"),
        "skills": target.get("skills", []),
        "events_completed": len(completed),
        "total_hours": total_hours,
        "certificates_earned": len(completed),
        "completed_events": completed,
    }


@api.patch("/applications/{event_id}/{username}")
async def update_application(event_id: str, username: str, data: StatusInput, user: dict = Depends(current_user)):
    if user["role"] != "organizer":
        raise HTTPException(403, "Organizer access required")
    event = await db.events.find_one({"id": event_id}, {"_id": 0})
    if not event:
        raise HTTPException(404, "Event not found")
    if event.get("organizer") != user["username"]:
        raise HTTPException(403, "You can only manage applications on your own events")
    updated = await db.applications.update_one({"event_id": event_id, "username": username}, {"$set": {"status": data.status}})
    if updated.matched_count == 0:
        raise HTTPException(404, "Application not found")
    return {"ok": True}


@api.post("/events/{event_id}/complete")
async def complete(event_id: str, data: CompleteInput, user: dict = Depends(current_user)):
    if user["role"] != "organizer":
        raise HTTPException(403, "Organizer access required")
    event = await db.events.find_one({"id": event_id}, {"_id": 0})
    if not event:
        raise HTTPException(404, "Event not found")
    if event.get("organizer") != user["username"]:
        raise HTTPException(403, "You can only mark completion on your own events")
    updated = await db.applications.update_one(
        {"event_id": event_id, "username": data.username, "status": "accepted"},
        {"$set": {"status": "completed", "hours": data.hours, "notes": data.notes}},
    )
    if updated.matched_count == 0:
        raise HTTPException(409, "This volunteer must be accepted before completion can be recorded")
    await db.events.update_one({"id": event_id}, {"$set": {"status": "completed"}})
    return {"ok": True}


@api.get("/certificates")
async def certificates(user: dict = Depends(current_user)):
    rows = await db.applications.find({"username": user["username"], "status": "completed"}, {"_id": 0}).to_list(100)
    result = []
    for row in rows:
        event = await db.events.find_one({"id": row["event_id"]}, {"_id": 0})
        if not event:
            continue
        result.append({"event_id": row["event_id"], "title": event.get("title", "Campus Event"), "hours": row.get("hours", 0), "date": event.get("date", "")})
    return result


def build_certificate_pdf(name: str, event_title: str, hours: float, event_date: str) -> bytes:
    buf = io.BytesIO()
    pdf = canvas.Canvas(buf, pagesize=landscape(letter))
    width, height = landscape(letter)

    # Paper background
    pdf.setFillColor(HexColor("#f7f8f5"))
    pdf.rect(0, 0, width, height, fill=1, stroke=0)

    # Deep green frame
    pdf.setStrokeColor(HexColor("#125c4f"))
    pdf.setLineWidth(3)
    pdf.rect(36, 36, width - 72, height - 72, fill=0, stroke=1)
    pdf.setStrokeColor(HexColor("#cce96d"))
    pdf.setLineWidth(1)
    pdf.rect(52, 52, width - 104, height - 104, fill=0, stroke=1)

    # Brand mark top-left
    pdf.setFillColor(HexColor("#125c4f"))
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(80, height - 90, "SKILLMATCH")
    pdf.setFillColor(HexColor("#8a9690"))
    pdf.setFont("Helvetica", 9)
    pdf.drawString(80, height - 104, "MIT-WPU · CAMPUS EVENTS OFFICE")

    # Eyebrow
    pdf.setFillColor(HexColor("#8a9690"))
    pdf.setFont("Helvetica", 11)
    pdf.drawCentredString(width / 2, height - 170, "CERTIFICATE OF COMPLETION")

    # Big title
    pdf.setFillColor(HexColor("#17212b"))
    pdf.setFont("Helvetica-Bold", 34)
    pdf.drawCentredString(width / 2, height - 215, "This is presented to")

    # Recipient name
    pdf.setFillColor(HexColor("#125c4f"))
    pdf.setFont("Helvetica-Bold", 46)
    pdf.drawCentredString(width / 2, height - 275, name)

    # Underline under name
    pdf.setStrokeColor(HexColor("#cce96d"))
    pdf.setLineWidth(2)
    pdf.line(width / 2 - 200, height - 290, width / 2 + 200, height - 290)

    # Body copy
    pdf.setFillColor(HexColor("#4a5450"))
    pdf.setFont("Helvetica", 14)
    body = f"for contributing {hours:g} hours as a student volunteer at"
    pdf.drawCentredString(width / 2, height - 325, body)

    pdf.setFillColor(HexColor("#17212b"))
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawCentredString(width / 2, height - 355, event_title)

    pdf.setFillColor(HexColor("#8a9690"))
    pdf.setFont("Helvetica", 11)
    pdf.drawCentredString(width / 2, height - 380, f"held on {event_date or 'campus'}")

    # Signature line
    pdf.setStrokeColor(HexColor("#17212b"))
    pdf.setLineWidth(1)
    pdf.line(width - 320, 115, width - 100, 115)
    pdf.setFont("Helvetica", 10)
    pdf.setFillColor(HexColor("#4a5450"))
    pdf.drawString(width - 320, 100, "Campus Events Office · MIT-WPU, Pune")

    pdf.line(100, 115, 320, 115)
    pdf.drawString(100, 100, f"Issued on {datetime.now(timezone.utc).strftime('%d %b %Y')}")

    # Accent dot
    pdf.setFillColor(HexColor("#cce96d"))
    pdf.circle(width - 90, height - 90, 10, fill=1, stroke=0)

    pdf.showPage()
    pdf.save()
    buf.seek(0)
    return buf.getvalue()


@api.get("/certificates/{event_id}")
async def certificate(event_id: str, user: dict = Depends(current_user)):
    row = await db.applications.find_one({"event_id": event_id, "username": user["username"], "status": "completed"}, {"_id": 0})
    event = await db.events.find_one({"id": event_id}, {"_id": 0})
    if not row or not event:
        raise HTTPException(404, "Certificate is not ready yet")
    pdf_bytes = build_certificate_pdf(
        name=user["name"],
        event_title=event["title"],
        hours=row.get("hours", 0),
        event_date=event.get("date", ""),
    )
    safe = event_id.replace("/", "-")
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="skillmatch-{safe}.pdf"'},
    )


app.include_router(api)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
