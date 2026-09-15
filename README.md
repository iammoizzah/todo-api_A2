# Task API

A small CRUD API for managing a to-do list, secured with **Supabase Auth**.
Built with **FastAPI** for the FlyRank Internship — Backend Track
(Assignments A1: CRUD, A4: Auth).

Tasks are stored **in memory** (a plain Python list) — there is no database
yet, so task data is lost when the server restarts. User accounts, however,
live in Supabase and persist normally.

We never hash a password or verify a JWT's signature ourselves — every
credential and every token is forwarded straight to **Supabase**, which does
that work for us. Our job is just: send credentials, verify tokens, open or
refuse the door.

## Requirements

- Python 3.10+
- A free [Supabase](https://supabase.com) project

## Setup

1. **Create a Supabase project** at [supabase.com](https://supabase.com) (free, no card).
2. In your Supabase Dashboard: **Project Settings → API**, copy your **Project URL**
   and **anon public key** (never the `service_role` key).
3. In your Supabase Dashboard: **Authentication → Sign In / Providers → Email**,
   turn **"Confirm email" off** for this practice project, so a fresh signup can
   log in immediately.
4. Copy `.env.example` to `.env` and fill in your real values:
   ```
   SUPABASE_URL=https://your-project-ref.supabase.co
   SUPABASE_KEY=your-anon-public-key
   PORT=8000
   ```
   `.env` is git-ignored — it will never be committed. Only `.env.example`
   (with placeholder values) is tracked.
5. Install dependencies and run:
   ```bash
   pip install -r requirements.txt
   uvicorn main:app --reload
   ```

The server starts on **http://localhost:8000**. Interactive Swagger docs
(with a bearer-token "Authorize" padlock) are at **http://localhost:8000/docs**.

## Endpoints

| Method | Path                   | Description                          | Auth required | Success | Errors |
|--------|------------------------|---------------------------------------|:--:|---------|--------|
| GET    | `/`                    | API info                              | – | 200 | — |
| GET    | `/health`              | Health check                          | – | 200 | — |
| GET    | `/public/info`         | Open info, anyone can read            | – | 200 | — |
| POST   | `/auth/signup`         | Create a new account                  | – | 201 | 400 missing email/password |
| POST   | `/auth/login`          | Log in, returns access + refresh token| – | 200 | 400 missing input, 401 bad credentials |
| POST   | `/auth/logout`         | End the session                       | ✅ | 204 | 401 missing/invalid token |
| GET    | `/protected/profile`   | Current user's profile                | ✅ | 200 | 401 missing/invalid token |
| GET    | `/protected/dashboard` | Second protected route (proves the auth guard is reusable) | ✅ | 200 | 401 missing/invalid token |
| GET    | `/tasks`               | List all tasks                        | – | 200 | — |
| GET    | `/tasks/{id}`          | Get one task                          | – | 200 | 404 if id doesn't exist |
| POST   | `/tasks`               | Create a task (`{"title": "..."}`)    | – | 201 | 400 if title missing/empty |
| PUT    | `/tasks/{id}`          | Update a task's title and/or done     | – | 200 | 404 if id doesn't exist, 400 if body invalid |
| DELETE | `/tasks/{id}`          | Delete a task                         | – | 204 | 404 if id doesn't exist |

Routes marked ✅ require `Authorization: Bearer <access_token>`. All errors
return JSON in the shape `{"error": "..."}`.

## Trying the full auth flow with curl

```bash
# 1. Sign up
curl -i -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# 2. Log in — copy the access_token from the response
curl -i -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# 3. Call a protected route with that token
curl -i http://localhost:8000/protected/profile \
  -H "Authorization: Bearer PASTE_YOUR_ACCESS_TOKEN_HERE"

# 4. Tamper with one character of the token and try again -> 401
curl -i http://localhost:8000/protected/profile \
  -H "Authorization: Bearer PASTE_YOUR_ACCESS_TOKEN_HERE_but_wrong"
```

### Example: curl -i output (401, no token)

```
$ curl -i http://localhost:8000/protected/profile
HTTP/1.1 401 Unauthorized
content-type: application/json

{"error":"Access token required"}
```

## Trying it in Swagger UI

1. Run the server (see Setup above).
2. Open http://localhost:8000/docs.
3. Run `POST /auth/signup` then `POST /auth/login` via "Try it out"; copy the
   `access_token` from the login response.
4. Click the **Authorize** padlock (top right), paste the token, click Authorize.
5. Run `GET /protected/profile` via "Try it out" — no need to paste the header
   manually, Swagger attaches it for you.

**Screenshot:** _add a screenshot of `/docs` here (e.g. `swagger.png`) showing
the Authorize dialog and a successful `/protected/profile` call — take it on
your own machine after running the server locally with a real Supabase project._

## Why the server never sees a raw password

Supabase Auth stores accounts and hashes passwords; this server only ever
forwards the email/password Supabase's SDK, and later verifies the JWT it
hands back. If this server's code were ever leaked, no passwords would leak
with it.

## The mortality experiment

Create a task, restart the server, then `GET /tasks` — the task is gone,
because it only ever lived in a Python list in memory. Your **user account**,
however, survives a restart, because it lives in Supabase, not in this
server's memory. That's the whole point of Week 3's database work: giving
tasks the same permanence users already have.
