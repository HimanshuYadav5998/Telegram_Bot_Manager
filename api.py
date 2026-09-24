import asyncio
import hashlib
import os
import secrets
import subprocess
import sys
import threading
from pathlib import Path
from typing import Optional

import httpx
from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import database as db

# ── Resolve paths ─────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
DIST_DIR   = BASE_DIR / "dashboard" / "dist"

# ── Init DB ───────────────────────────────────────────────────────────────────
db.init_db()

app = FastAPI(title="Telegram Bot Dashboard API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# All API endpoints are mounted under /api so the React frontend (which calls
# /api/... in both dev and prod) works without a proxy in production.
from fastapi import APIRouter as _APIRouter
api_router = _APIRouter(prefix="/api")

# ── Token store (in-memory; one admin session at a time) ──────────────────────
_active_tokens: set[str] = set()
_bearer = HTTPBearer()



def _hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _verify_token(credentials: HTTPAuthorizationCredentials = Security(_bearer)):
    if credentials.credentials not in _active_tokens:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return credentials.credentials


# ── Bot process management ────────────────────────────────────────────────────
_bot_process: Optional[subprocess.Popen] = None
_bot_lock = threading.Lock()
_auto_restart = True   # set False when user explicitly stops from dashboard
_watchdog_started = False


def _is_bot_running() -> bool:
    global _bot_process
    return _bot_process is not None and _bot_process.poll() is None


def _start_bot_process() -> subprocess.Popen:
    """Spawn bot.py as a subprocess and return the Popen handle."""
    return subprocess.Popen(
        [sys.executable, "bot.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def _watchdog():
    """
    Background thread: watches the bot process.
    If it dies and _auto_restart is True, waits 10s and restarts it.
    Logs output lines in real-time so crashes are visible.
    """
    global _bot_process, _auto_restart

    while True:
        # Drain stdout while process is running
        if _bot_process and _bot_process.stdout:
            try:
                for line in _bot_process.stdout:
                    line = line.rstrip()
                    if line:
                        print(f"[BOT] {line}", flush=True)
            except Exception:
                pass

        # Wait for process to finish
        if _bot_process:
            _bot_process.wait()
            exit_code = _bot_process.returncode
        else:
            threading.Event().wait(5)
            continue

        if not _auto_restart:
            # Intentional stop — don't restart
            db.set_config("bot_status", "stopped")
            break

        # Unexpected exit → log and restart
        print(f"[WATCHDOG] ⚠️  Bot exited with code {exit_code}. Restarting in 10s…", flush=True)
        db.set_config("bot_status", "restarting")
        db.log_event(event_type="error",
                     detail=f"Bot process exited (code {exit_code}). Auto-restarting in 10s.")
        threading.Event().wait(10)

        with _bot_lock:
            if not _auto_restart:
                break
            try:
                _bot_process = _start_bot_process()
                db.set_config("bot_status", "running")
                db.log_event(event_type="bot_start",
                             detail="Bot auto-restarted by watchdog after crash")
                print("[WATCHDOG] ✅ Bot restarted.", flush=True)
            except Exception as e:
                print(f"[WATCHDOG] ❌ Failed to restart bot: {e}", flush=True)
                db.log_event(event_type="error", detail=f"Watchdog restart failed: {e}")


# ── Pydantic models ───────────────────────────────────────────────────────────
class LoginPayload(BaseModel):
    username: Optional[str] = "admin"
    password: str

class ChangePasswordPayload(BaseModel):
    new_password: str
    username: Optional[str] = "admin"

class AdminCreatePayload(BaseModel):
    username: str
    password: str

class PreviewCreatePayload(BaseModel):
    name: str
    type: str # 'file_id' or 'url'
    content: str
# ── Auth ──────────────────────────────────────────────────────────────────────
@api_router.post("/auth/login")
def login(payload: LoginPayload):
    username = payload.username or "admin"
    
    # Ensure at least one admin exists
    if len(db.get_all_admins()) == 0:
        db.add_admin("admin", _hash_pw("admin123"))

    admin = db.get_admin(username)
    if not admin:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if _hash_pw(payload.password) != admin["password_hash"]:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = secrets.token_urlsafe(32)
    _active_tokens.add(token)
    db.log_event(event_type="admin_login", detail=f"Admin '{username}' logged into dashboard")
    return {"token": token}


@api_router.post("/auth/logout")
def logout(token: str = Depends(_verify_token)):
    _active_tokens.discard(token)
    return {"ok": True}


@api_router.post("/auth/change-password")
def change_password(
    payload: ChangePasswordPayload,
    token: str = Depends(_verify_token),
):
    if len(payload.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    username = payload.username or "admin"
    admin = db.get_admin(username)
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
        
    db._lock.acquire()
    try:
        conn = db.get_conn()
        conn.execute("UPDATE admins SET password_hash=? WHERE username=?", (_hash_pw(payload.new_password), username))
        conn.commit()
        conn.close()
    finally:
        db._lock.release()
        
    # Revoke all existing sessions
    _active_tokens.clear()
    db.log_event(event_type="config_change", detail=f"Password changed for admin '{username}'")
    return {"ok": True}

# ── Admins Management ─────────────────────────────────────────────────────────

@api_router.get("/admins")
def get_admins(token: str = Depends(_verify_token)):
    return db.get_all_admins()

@api_router.post("/admins")
def create_admin(payload: AdminCreatePayload, token: str = Depends(_verify_token)):
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    success = db.add_admin(payload.username, _hash_pw(payload.password))
    if not success:
        raise HTTPException(status_code=400, detail="Username already exists")
    db.log_event(event_type="config_change", detail=f"New admin created: {payload.username}")
    return {"ok": True}

@api_router.delete("/admins/{username}")
def remove_admin(username: str, token: str = Depends(_verify_token)):
    if username == "admin":
        raise HTTPException(status_code=400, detail="Cannot delete default admin")
    db.delete_admin(username)
    db.log_event(event_type="config_change", detail=f"Admin deleted: {username}")
    return {"ok": True}

# ── Previews Management ───────────────────────────────────────────────────────

@api_router.get("/previews")
def list_previews(token: str = Depends(_verify_token)):
    return db.get_previews()

@api_router.post("/previews")
def create_preview(payload: PreviewCreatePayload, token: str = Depends(_verify_token)):
    preview_id = secrets.token_hex(4) # Generate short unique ID
    db.create_preview(preview_id, payload.name, payload.type, payload.content)
    db.log_event(event_type="preview_created", detail=f"Created preview: {payload.name}")
    return {"id": preview_id}

@api_router.post("/previews/{preview_id}/toggle")
def toggle_preview(preview_id: str, active: dict, token: str = Depends(_verify_token)):
    # active = {"is_active": True/False}
    is_active = 1 if active.get("is_active", True) else 0
    db.toggle_preview(preview_id, is_active)
    db.log_event(event_type="preview_updated", detail=f"Toggled preview {preview_id} to {bool(is_active)}")
    return {"ok": True}

@api_router.delete("/previews/{preview_id}")
def delete_preview(preview_id: str, token: str = Depends(_verify_token)):
    db.delete_preview(preview_id)
    db.log_event(event_type="preview_deleted", detail=f"Deleted preview: {preview_id}")
    return {"ok": True}


# ── Stats ─────────────────────────────────────────────────────────────────────
@api_router.get("/stats")
def get_stats(token: str = Depends(_verify_token)):
    return db.get_stats()


# ── Users ─────────────────────────────────────────────────────────────────────
@api_router.get("/users")
def get_users(search: str = "", token: str = Depends(_verify_token)):
    return db.get_all_users(search=search)


@api_router.post("/users/{user_id}/status")
def set_user_status(
    user_id: int,
    payload: UserStatusPayload,
    token: str = Depends(_verify_token),
):
    db.set_user_status(user_id, payload.status)
    db.log_event(event_type="user_status_change", user_id=user_id,
                 detail=f"Status set to {payload.status} via dashboard")
    return {"ok": True, "user_id": user_id, "status": payload.status}


# ── Join Requests ─────────────────────────────────────────────────────────────
@api_router.get("/join-requests")
def get_join_requests(status: str = None, token: str = Depends(_verify_token)):
    return db.get_join_requests(status=status)


@api_router.post("/join-requests/{user_id}/approve")
def approve_request(user_id: int, token: str = Depends(_verify_token)):
    db.update_join_request_status(user_id, "approved")
    db.log_event(event_type="approved", user_id=user_id,
                 detail="Manually approved via dashboard")
    return {"ok": True}


@api_router.post("/join-requests/{user_id}/reject")
def reject_request(user_id: int, token: str = Depends(_verify_token)):
    db.update_join_request_status(user_id, "rejected")
    db.log_event(event_type="rejected", user_id=user_id,
                 detail="Manually rejected via dashboard")
    return {"ok": True}


# ── Events / Activity Feed ─────────────────────────────────────────────────────
@api_router.get("/events")
def get_events(limit: int = 50, token: str = Depends(_verify_token)):
    return db.get_recent_events(limit=limit)


# ── Bot Controls ──────────────────────────────────────────────────────────────
@api_router.get("/bot/status")
def bot_status(token: str = Depends(_verify_token)):
    running = _is_bot_running()
    if running:
        status = "running"
    elif _auto_restart and _watchdog_started:
        # Watchdog is active — bot may be in a restart cycle
        status = db.get_config("bot_status") or "restarting"
    else:
        status = "stopped"
    db.set_config("bot_status", status)
    return {"status": status}


@api_router.post("/bot/start")
def bot_start(token: str = Depends(_verify_token)):
    global _bot_process, _auto_restart, _watchdog_started
    with _bot_lock:
        if _is_bot_running():
            return {"ok": False, "message": "Bot is already running"}
        # Validate token before starting
        bot_token = db.get_config("bot_token") or ""
        if not bot_token or bot_token == "YOUR_BOT_TOKEN":
            raise HTTPException(
                status_code=400,
                detail="Bot token not set! Go to Settings and enter your bot token first."
            )
        try:
            _auto_restart = True
            _bot_process = _start_bot_process()
            db.set_config("bot_status", "running")
            db.log_event(event_type="bot_start", detail="Bot started via dashboard")

            # Start watchdog thread if not already running
            if not _watchdog_started:
                t = threading.Thread(target=_watchdog, daemon=True)
                t.start()
                globals()["_watchdog_started"] = True

            return {"ok": True, "message": "Bot started successfully", "pid": _bot_process.pid}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/bot/stop")
def bot_stop(token: str = Depends(_verify_token)):
    global _bot_process, _auto_restart, _watchdog_started
    with _bot_lock:
        if not _is_bot_running():
            return {"ok": False, "message": "Bot is not running"}
        # Disable auto-restart BEFORE killing so watchdog won't revive it
        _auto_restart = False
        _watchdog_started = False
        _bot_process.terminate()
        try:
            _bot_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _bot_process.kill()
        db.set_config("bot_status", "stopped")
        db.log_event(event_type="bot_stop", detail="Bot stopped via dashboard")
        return {"ok": True, "message": "Bot stopped"}


# ── Broadcast ─────────────────────────────────────────────────────────────────
@api_router.post("/broadcast")
async def broadcast(payload: BroadcastPayload, token: str = Depends(_verify_token)):
    bot_token = db.get_config("bot_token")
    if not bot_token or bot_token == "YOUR_BOT_TOKEN":
        raise HTTPException(status_code=400, detail="Bot token not configured. Set it in Settings.")

    users = db.get_all_users()
    sent, failed = 0, 0

    async with httpx.AsyncClient() as client:
        for user in users:
            try:
                resp = await client.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    json={"chat_id": user["user_id"], "text": payload.message},
                )
                if resp.status_code == 200:
                    sent += 1
                else:
                    failed += 1
            except Exception:
                failed += 1

    db.log_event(
        event_type="broadcast",
        detail=f"Sent to {sent}, failed {failed}. Preview: {payload.message[:80]}"
    )
    return {"ok": True, "sent": sent, "failed": failed}


# ── Config ────────────────────────────────────────────────────────────────────
@api_router.get("/config")
def get_config(token: str = Depends(_verify_token)):
    raw = db.get_config("bot_token") or ""
    return {
        "channel_link": db.get_config("channel_link"),
        "bot_token":    ("***" + raw[-4:]) if len(raw) > 4 else "not set",
    }


@api_router.put("/config")
def update_config(payload: ConfigPayload, token: str = Depends(_verify_token)):
    if payload.channel_link is not None:
        db.set_config("channel_link", payload.channel_link)
        db.log_event(event_type="config_change",
                     detail=f"Channel link updated: {payload.channel_link}")
    if payload.bot_token is not None:
        db.set_config("bot_token", payload.bot_token)
        db.log_event(event_type="config_change", detail="Bot token updated via dashboard")
    return {"ok": True}


# ── Wire up the /api router ───────────────────────────────────────────────────
app.include_router(api_router)

# ── Serve React frontend (production build) ───────────────────────────────────
if DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="assets")

    @app.get("/", include_in_schema=False)
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str = ""):
        """Catch-all: serve React index.html for any non-API route."""
        if full_path.startswith(("api/", "api", "docs", "openapi")):
            raise HTTPException(status_code=404)
        index = DIST_DIR / "index.html"
        if index.exists():
            return FileResponse(str(index))
        return {"error": "Frontend not built. Run: cd dashboard && npm run build"}


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=False)
