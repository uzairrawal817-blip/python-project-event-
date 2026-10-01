# SkillMatch PRD

## Original problem statement
Build a refined, reliable website for a college campus event and volunteer skill-matching system. It connects organizers with student volunteers based on skills and generates completion certificates.

## Architecture decisions
- FastAPI backend with MongoDB persistence using the existing environment connection.
- React frontend using the existing CRA setup and the external backend URL.
- Lightweight username/password session using an HTTP-only cookie and JWT.
- Seeded demo organizer, volunteer, events, applications, and certificate flow.

## User personas
- Student volunteers discovering meaningful campus opportunities and earning certificates.
- Event organizers creating events, reviewing applications, and recording completion.

## Core requirements
- Role-aware volunteer and organizer experiences.
- Event discovery, search, skill matching, signup, application review, completion, and certificate download.
- Responsive, polished academic/campus-event interface.

## What's implemented (2026-02-18)
- Replaced starter screen with responsive SkillMatch dashboard and sign-in/register experience.
- Added seeded MongoDB data, auth endpoints, event APIs, application management, and text certificate downloads.
- Added organizer event creation and volunteer management, with mobile-friendly layouts and descriptive test IDs.

## Prioritized backlog
- P0: Add PDF certificate export and production-grade auth hardening.
- P1: Add event editing, richer volunteer profiles, notifications, and advanced filters.
- P2: Add analytics, attendance QR check-in, and campus branding controls.

## Next tasks
- Validate the complete volunteer and organizer flows against the seeded accounts.
- Replace text certificate response with a printable PDF template.
- Add organizer event editing and volunteer profile editing.