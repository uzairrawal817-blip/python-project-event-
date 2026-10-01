# SkillMatch — Campus Event & Volunteer Management System

A clean, responsive full‑stack web app that connects **event organizers** with **student volunteers** on a college campus, matches them by skills, runs attendance via QR check‑in, and auto‑generates printable PDF completion certificates.

Built as a school project for **MIT‑WPU Pune**.

---

## ✨ Features

- 🔐 **Role‑aware auth** (JWT in httpOnly cookie + bcrypt): student volunteer vs event organizer
- 📅 **Event CRUD** — organizers create, edit, delete campus events with required skills + capacity
- 🧩 **Skill matching** — volunteers see which events are a "Great match" for their skills
- ✍️ **Applications flow** — apply → organizer accepts / rejects → mark complete
- 📱 **QR attendance check‑in** — each event has a 6‑char code; volunteers scan or type it to self‑mark completion
- 📜 **Printable PDF certificates** — ReportLab generates landscape certificates with MIT‑WPU branding
- 📊 **Insights dashboards**
  - *Organizer*: hours contributed, unique volunteers, skill‑coverage bars, top‑5 leaderboard, per‑event breakdown
  - *Volunteer*: events applied / accepted / completed, hours earned, certificates, matching opportunities, recent activity
- 👤 **Clickable volunteer profiles** — organizers can tap any applicant to see completed events, hours, certificates, skills
- 🧑‍💻 **Profile editing** — name, department, skills

---

## 🧱 Tech stack

| Layer     | Choice                                                                 |
| --------- | ---------------------------------------------------------------------- |
| Frontend  | React 19 (CRA + Craco), Tailwind CSS, lucide‑react, qrcode.react, axios |
| Backend   | FastAPI, Motor (async MongoDB driver), Pydantic v2, PyJWT, bcrypt, ReportLab |
| Database  | MongoDB                                                                |
| Styling   | Hand‑rolled CSS + Tailwind utilities, custom green/lime MIT‑WPU palette |

---

## 📂 Project structure

```
skillmatch/
├── backend/
│   ├── server.py            # All FastAPI routes (auth, events, apps, insights, PDF)
│   ├── requirements.txt
│   └── .env.example         # Copy to .env and fill in
├── frontend/
│   ├── src/
│   │   ├── App.js           # Main React app (all screens + modals)
│   │   ├── App.css          # Component + utility styles
│   │   ├── index.js
│   │   ├── index.css        # Tailwind layers
│   │   └── components/ui/   # shadcn/ui primitives (optional, pre‑installed)
│   ├── package.json
│   ├── tailwind.config.js
│   ├── craco.config.js
│   └── .env.example
└── README.md
```

---

## 🚀 Local setup

### Prerequisites
- **Python 3.11+**
- **Node 18+** and **Yarn** (`npm i -g yarn`)
- **MongoDB** running locally (`mongodb://localhost:27017`) — or any Atlas URI

### 1. Backend

```bash
cd backend
cp .env.example .env
# edit .env and set JWT_SECRET to a random 48+ char string:
python -c "import secrets; print(secrets.token_urlsafe(48))"

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

API lives at **`http://localhost:8001/api`**. First boot auto‑seeds demo data:
- Volunteer login — `maya` / `maya1234`
- Organizer login — `campusadmin` / `admin1234`

### 2. Frontend

```bash
cd frontend
cp .env.example .env
# edit .env and set REACT_APP_BACKEND_URL=http://localhost:8001

yarn install
yarn start
```

Open **http://localhost:3000**.

---

## 🔑 Environment variables

### `backend/.env`
| Key           | Required | Example                                              |
| ------------- | -------- | ---------------------------------------------------- |
| `MONGO_URL`   | ✅       | `mongodb://localhost:27017`                          |
| `DB_NAME`     | ✅       | `skillmatch`                                         |
| `JWT_SECRET`  | ✅       | 48+ char random string (`secrets.token_urlsafe(48)`) |
| `CORS_ORIGINS`| ❌       | Comma‑sep origins. Default `*` (dev only)            |

### `frontend/.env`
| Key                     | Example                   |
| ----------------------- | ------------------------- |
| `REACT_APP_BACKEND_URL` | `http://localhost:8001`   |

> ⚠️ **Security**: never commit real `.env` files. The repo ships only `.env.example`.

---

## 🧭 API reference (prefix `/api`)

### Auth
| Method | Path             | Who          | Purpose                        |
| ------ | ---------------- | ------------ | ------------------------------ |
| POST   | `/auth/login`    | Public       | Sets `skillmatch_token` cookie |
| POST   | `/auth/register` | Public       | Create user + login            |
| POST   | `/auth/logout`   | Any          | Clear cookie                   |
| GET    | `/auth/me`       | Any          | Current user profile           |
| PATCH  | `/auth/me`       | Any          | Update name / dept / skills    |

### Events
| Method | Path                     | Who       | Purpose                       |
| ------ | ------------------------ | --------- | ----------------------------- |
| GET    | `/events`                | Any       | List all events               |
| POST   | `/events`                | Organizer | Create event                  |
| PATCH  | `/events/{id}`           | Owner org | Edit event                    |
| DELETE | `/events/{id}`           | Owner org | Delete event                  |
| POST   | `/events/{id}/apply`     | Volunteer | Apply                         |
| POST   | `/events/{id}/checkin`   | Volunteer | QR / code check‑in → complete |
| POST   | `/events/{id}/complete`  | Owner org | Mark volunteer complete       |

### Applications & insights
| Method | Path                                         | Who               | Purpose                       |
| ------ | -------------------------------------------- | ----------------- | ----------------------------- |
| GET    | `/organizer/applicants`                      | Organizer         | List applicants on own events |
| PATCH  | `/applications/{event_id}/{username}`        | Owner org         | Accept / reject               |
| GET    | `/certificates`                              | Volunteer         | Earned certificate list       |
| GET    | `/certificates/{event_id}`                   | Volunteer         | **Download PDF**              |
| GET    | `/insights/organizer`                        | Organizer         | Dashboard stats               |
| GET    | `/insights/volunteer`                        | Volunteer         | Dashboard stats               |
| GET    | `/users/{username}`                          | Self / scoped org | Public profile view           |

---

## 🔒 Security notes

| Topic             | Status                                                                 |
| ----------------- | ---------------------------------------------------------------------- |
| JWT secret        | Loaded from `JWT_SECRET` env; **server refuses to start if unset or <32 chars** |
| Password storage  | `bcrypt` with per‑user salt                                            |
| Cookies           | `HttpOnly`, `SameSite=Lax`. Add `Secure=True` for HTTPS prod.          |
| Role gating       | Enforced server‑side on every mutation                                 |
| Event ownership   | PATCH/DELETE/complete/applications all check `event.organizer == user` |
| Demo accounts     | Seeded on first boot — **remove or rotate before public launch**       |
| CORS              | Default `*`; set `CORS_ORIGINS` to your frontend URL for prod          |

---

## 🧪 Tests

Backend regression tests (pytest):

```bash
cd backend
pytest -q
```

Suites included:
- `tests/test_skillmatch_api.py` — core auth / event / cert flow
- `tests/test_enhancements.py`   — PDF cert, event edit/delete, profile edit, QR check‑in
- `tests/test_insights.py`       — insights endpoints + volunteer profile view

---

## 🙌 Credits

- Dome photograph © Wikimedia Commons contributors — MIT World Peace University, CC BY‑SA
- Icons: [Lucide](https://lucide.dev)
- QR SVGs: [qrcode.react](https://github.com/zpao/qrcode.react)

---

## 📝 License

MIT — add a `LICENSE` file when you push to GitHub.
