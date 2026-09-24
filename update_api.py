import re

with open('api.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update LoginPayload and ChangePasswordPayload, add new Payloads
models_replacement = """# ── Pydantic models ───────────────────────────────────────────────────────────
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
"""
content = re.sub(r'# ── Pydantic models .*?(?=# ── Auth)', models_replacement, content, flags=re.DOTALL)


# 2. Update Auth endpoints
auth_replacement = """# ── Auth ──────────────────────────────────────────────────────────────────────
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

"""
content = re.sub(r'# ── Auth ──────────────────────────────────────────────────────────────────────.*?# ── Stats', auth_replacement + "\n# ── Stats", content, flags=re.DOTALL)

with open('api.py', 'w', encoding='utf-8') as f:
    f.write(content)
