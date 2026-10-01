# SkillMatch Authentication Testing

Seeded accounts are documented in `/app/memory/test_credentials.md`.

1. POST `/api/auth/login` with username and password; verify an HTTP-only `skillmatch_token` cookie.
2. GET `/api/auth/me` using that cookie; verify role, name, department, and skills.
3. POST `/api/auth/logout`; verify the session is cleared.
4. POST `/api/auth/register`; verify a new account can load the dashboard.
5. Attempt invalid credentials and verify a readable 401 error.