# SkillMatch PRD

## Original problem statement
Build a refined, reliable website for a college campus event and volunteer skill-matching system for MIT-WPU Pune. Connects organizers with student volunteers based on skills and generates completion certificates.

## Architecture decisions
- FastAPI backend with MongoDB persistence.
- React frontend using CRA + Tailwind + lucide-react.
- JWT via httpOnly cookie `skillmatch_token`.
- Reportlab for PDF certificates; qrcode.react for QR codes.

## User personas
- Student volunteers discovering campus opportunities and earning PDF certificates.
- Event organizers creating/editing events, approving volunteers, and running QR check-ins.

## Core requirements
- Role-aware volunteer and organizer experiences.
- Event CRUD, discovery/search, apply, review, QR check-in, PDF certificates.
- Responsive MIT-WPU branded UI.

## What's implemented
- 2026-02-18: Initial SkillMatch dashboard, auth, event + application flows, text certificates.
- 2026-02-18 (today): PDF certificates, event edit/delete, profile editing, QR attendance check-in, MIT-WPU dome imagery.

## Prioritized backlog
- P1: Notifications panel for status changes.
- P1: Advanced filters (date range, department, matched-only).
- P2: Organizer analytics dashboard (volunteers per event, hours contributed).
- P2: Shareable certificate verification URL for recruiters.
