from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from supabase_client import supabase

app = FastAPI(title="Task API", version="1.0")
bearer_scheme = HTTPBearer(
    auto_error=False,
    description="Paste the access_token you got back from POST /auth/login",
)


@app.on_event("startup")
def on_startup():
    print("Server running and connected to Supabase")


class TaskCreate(BaseModel):
    title: Optional[str] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    done: Optional[bool] = None


class AuthCredentials(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException):
    # The assignment wants {"error": "..."} instead of FastAPI's default {"detail": "..."}
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


tasks = [
    {"id": 1, "title": "Buy milk", "done": False},
    {"id": 2, "title": "Write README", "done": False},
    {"id": 3, "title": "Walk the dog", "done": True},
]
next_id = 4


def find_task(task_id: int):
    """Return the task with this id, or None if it doesn't exist."""
    return next((t for t in tasks if t["id"] == task_id), None)


@app.get("/", summary="API info")
def root():
    """Describes what this API is and where to find its main resource."""
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}


@app.get("/health", summary="Health check")
def health():
    """Used to confirm the server is up and responding."""
    return {"status": "ok"}


@app.get("/tasks", summary="List all tasks")
def list_tasks():
    """Returns every task currently in memory."""
    return tasks


@app.get("/tasks/{task_id}", summary="Get one task")
def get_task(task_id: int):
    task = find_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task


@app.post("/tasks", status_code=201, summary="Create a task")
def create_task(body: TaskCreate):
    """Creates a task from a JSON body like {"title": "Buy milk"}. Title is required."""
    global next_id
    if not body.title or not body.title.strip():
        raise HTTPException(status_code=400, detail="title is required and cannot be empty")

    task = {"id": next_id, "title": body.title.strip(), "done": False}
    tasks.append(task)
    next_id += 1
    return task


@app.put("/tasks/{task_id}", summary="Update a task")
def update_task(task_id: int, body: TaskUpdate):
    """Updates a task's title and/or done status. At least one field is required."""
    task = find_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    if body.title is None and body.done is None:
        raise HTTPException(status_code=400, detail="provide title and/or done to update")
    if body.title is not None and not body.title.strip():
        raise HTTPException(status_code=400, detail="title cannot be empty")

    if body.title is not None:
        task["title"] = body.title.strip()
    if body.done is not None:
        task["done"] = body.done
    return task


@app.delete("/tasks/{task_id}", status_code=204, summary="Delete a task")
def delete_task(task_id: int):
    """Removes a task permanently. Returns no body on success."""
    task = find_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    tasks.remove(task)
    return None


# --- Auth: sign up & log in --------------------------------------------
# We never hash passwords or store credentials ourselves -- every call
# here is forwarded straight to Supabase, which does that work for us.

@app.post("/auth/signup", status_code=201, summary="Create a new account")
def signup(body: AuthCredentials):
    if not body.email or not body.password:
        raise HTTPException(status_code=400, detail="email and password are required")

    try:
        result = supabase.auth.sign_up({"email": body.email, "password": body.password})
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {"user": result.user}


@app.post("/auth/login", summary="Log in and receive a JWT")
def login(body: AuthCredentials):
    if not body.email or not body.password:
        raise HTTPException(status_code=400, detail="email and password are required")

    try:
        result = supabase.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid login credentials")

    return {
        "access_token": result.session.access_token,
        "refresh_token": result.session.refresh_token,
    }


# --- Public & protected gates -------------------------------------------

@app.get("/public/info", summary="Open, unauthenticated info")
def public_info():
    return {"message": "Welcome stranger! This info is public."}


def extract_bearer_token(creds: Optional[HTTPAuthorizationCredentials]) -> str:
    """Pulls the token out of the Authorization: Bearer <token> header. Raises 401 if missing."""
    if creds is None or not creds.credentials:
        raise HTTPException(status_code=401, detail="Access token required")
    return creds.credentials


def get_current_user(creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)):
    """Reusable auth guard: extracts + verifies the bearer token, returns the Supabase user.

    Apply with Depends(get_current_user) to any route that should require login --
    this is FastAPI's version of middleware, and it's the ONLY place token
    verification logic lives. Using HTTPBearer also makes Swagger UI show an
    "Authorize" padlock on every route that depends on this.
    """
    token = extract_bearer_token(creds)

    try:
        result = supabase.auth.get_user(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if result is None or result.user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return result.user


@app.get("/protected/profile", summary="Private profile data (auth required)")
def profile(user=Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "created_at": user.created_at}


@app.get("/protected/dashboard", summary="Another private route, reusing the same guard")
def dashboard(user=Depends(get_current_user)):
    """Proves the guard is reusable: zero new auth code, just Depends(get_current_user)."""
    return {"message": f"Welcome to your dashboard, {user.email}"}


@app.post("/auth/logout", status_code=204, summary="Log out (auth required)")
def logout(user=Depends(get_current_user)):
    try:
        supabase.auth.sign_out()
    except Exception:
        pass  # sign-out failing server-side doesn't need to block the client
    return None
