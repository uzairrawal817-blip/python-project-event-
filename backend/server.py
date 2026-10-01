from dotenv import load_dotenv
load_dotenv()

import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import bcrypt
import jwt
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field

ROOT_DIR = Path(__file__).parent
client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]
JWT_SECRET = os.environ.get("JWT_SECRET", "skillmatch-school-demo-secret")
JWT_ALGORITHM = "HS256"
app = FastAPI(title="SkillMatch API")
api = APIRouter(prefix="/api")

class LoginInput(BaseModel):
    username: str = Field(min_length=2, max_length=40)
    password: str = Field(min_length=4, max_length=100)

class RegisterInput(LoginInput):
    name: str = Field(min_length=2, max_length=80)
    role: str = Field(pattern="^(organizer|volunteer)$")
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

def public_user(user: dict) -> dict:
    return {"id": str(user.get("_id", user.get("id", user["username"]))), "username": user["username"], "name": user["name"], "role": user["role"], "department": user.get("department", ""), "skills": user.get("skills", [])}

def token_for(user: dict) -> str:
    return jwt.encode({"sub": user["username"], "exp": datetime.now(timezone.utc).timestamp() + 86400}, JWT_SECRET, algorithm=JWT_ALGORITHM)

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
            {"id": "event-python", "title": "Python for Everyone", "description": "A welcoming hands-on workshop helping first-years build their first useful script.", "date": "2025-09-18", "time": "10:00 AM", "location": "Innovation Lab · Block C", "required_skills": ["Python", "Public speaking"], "capacity": 12, "organizer": "campusadmin", "status": "open"},
            {"id": "event-fest", "title": "Founders Day Festival", "description": "Make the annual campus celebration unforgettable for 2,000 students.", "date": "2025-09-21", "time": "04:30 PM", "location": "Central Quad", "required_skills": ["Design", "Event planning"], "capacity": 30, "organizer": "campusadmin", "status": "open"},
            {"id": "event-green", "title": "Green Campus Drive", "description": "A morning of planting, cleanup, and small actions with a big campus impact.", "date": "2025-09-27", "time": "08:30 AM", "location": "North Garden", "required_skills": ["Teamwork"], "capacity": 25, "organizer": "campusadmin", "status": "open"},
        ])
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

async def event_payload(event: dict, user: Optional[dict] = None) -> dict:
    result = {k: event.get(k) for k in ["id", "title", "description", "date", "time", "location", "required_skills", "capacity", "organizer", "status"]}
    apps = await db.applications.find({"event_id": event["id"]}, {"_id": 0}).to_list(100)
    result["volunteers"] = len([a for a in apps if a.get("status") in ["accepted", "completed"]])
    result["application"] = next((a.get("status") for a in apps if user and a.get("username") == user.get("username")), None)
    result["match"] = bool(user and user.get("role") == "volunteer" and not event.get("required_skills") or user and set(s.lower() for s in event.get("required_skills", [])) & set(s.lower() for s in user.get("skills", [])))
    return result

@api.get("/events")
async def events(user: dict = Depends(current_user)):
    return [await event_payload(e, user) for e in await db.events.find({}, {"_id": 0}).sort("date", 1).to_list(100)]

@api.post("/events")
async def create_event(data: EventInput, user: dict = Depends(current_user)):
    if user["role"] != "organizer": raise HTTPException(403, "Only organizers can create events")
    event = data.model_dump() | {"id": "event-" + secrets.token_hex(4), "organizer": user["username"], "status": "open"}
    await db.events.insert_one(event)
    return await event_payload(event, user)

@api.post("/events/{event_id}/apply")
async def apply(event_id: str, user: dict = Depends(current_user)):
    if user["role"] != "volunteer": raise HTTPException(403, "Switch to volunteer mode to join an event")
    event = await db.events.find_one({"id": event_id}, {"_id": 0})
    if not event: raise HTTPException(404, "Event not found")
    if await db.applications.find_one({"event_id": event_id, "username": user["username"]}): raise HTTPException(409, "You already joined this event")
    await db.applications.insert_one({"event_id": event_id, "username": user["username"], "status": "pending", "hours": 0, "notes": ""})
    return {"ok": True}

@api.get("/organizer/applicants")
async def applicants(user: dict = Depends(current_user)):
    if user["role"] != "organizer": raise HTTPException(403, "Organizer access required")
    own = [e["id"] for e in await db.events.find({"organizer": user["username"]}, {"_id": 0, "id": 1}).to_list(100)]
    rows = []
    for app_row in await db.applications.find({"event_id": {"$in": own}}, {"_id": 0}).to_list(200):
        volunteer = await db.users.find_one({"username": app_row["username"]}, {"_id": 0})
        event = await db.events.find_one({"id": app_row["event_id"]}, {"_id": 0})
        rows.append({**app_row, "name": volunteer.get("name", app_row["username"]) if volunteer else app_row["username"], "skills": volunteer.get("skills", []) if volunteer else [], "event_title": event.get("title", "Event") if event else "Event"})
    return rows

@api.patch("/applications/{event_id}/{username}")
async def update_application(event_id: str, username: str, data: StatusInput, user: dict = Depends(current_user)):
    if user["role"] != "organizer": raise HTTPException(403, "Organizer access required")
    updated = await db.applications.update_one({"event_id": event_id, "username": username}, {"$set": {"status": data.status}})
    if updated.matched_count == 0:
        raise HTTPException(404, "Application not found")
    return {"ok": True}

@api.post("/events/{event_id}/complete")
async def complete(event_id: str, data: CompleteInput, user: dict = Depends(current_user)):
    if user["role"] != "organizer": raise HTTPException(403, "Organizer access required")
    updated = await db.applications.update_one({"event_id": event_id, "username": data.username, "status": "accepted"}, {"$set": {"status": "completed", "hours": data.hours, "notes": data.notes}})
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
        result.append({"event_id": row["event_id"], "title": event.get("title", "Campus Event"), "hours": row.get("hours", 0), "date": event.get("date", "")})
    return result

@api.get("/certificates/{event_id}", response_class=PlainTextResponse)
async def certificate(event_id: str, user: dict = Depends(current_user)):
    row = await db.applications.find_one({"event_id": event_id, "username": user["username"], "status": "completed"}, {"_id": 0})
    event = await db.events.find_one({"id": event_id}, {"_id": 0})
    if not row or not event: raise HTTPException(404, "Certificate is not ready yet")
    return f"SKILLMATCH\n\nCERTIFICATE OF COMPLETION\n\nThis certifies that {user['name']} contributed {row.get('hours', 0)} hours to {event['title']} on {event.get('date', '')}.\n\nCampus Events Office"

app.include_router(api)
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","), allow_methods=["*"], allow_headers=["*"])