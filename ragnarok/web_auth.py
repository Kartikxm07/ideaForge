"""Cookie sessions for the browser; existing bearer clients retain their own scope."""
from datetime import datetime, timedelta, timezone
import hashlib
import secrets
import sqlite3
import time
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator
from .store import now

COOKIE = "odin_session"


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=128)

    @field_validator("email")
    @classmethod
    def email_valid(cls, value):
        value = value.strip().lower()
        if "@" not in value or "." not in value.rsplit("@", 1)[1]:
            raise ValueError("Enter a valid email address")
        return value


class Registration(Credentials):
    name: str = Field(min_length=2, max_length=120)
    organization: str = Field(min_length=2, max_length=120)
    terms: bool


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    return salt + ":" + hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()


def install_auth(app, store):
    router = APIRouter(prefix="/api/v1/auth", tags=["Browser sessions"])

    def session(request: Request):
        raw = request.cookies.get(COOKIE, "")
        with store.connect() as db:
            row = db.execute("SELECT s.*,u.email,u.name,m.role FROM web_sessions s JOIN web_users u ON u.id=s.user_id JOIN web_members m ON m.user_id=s.user_id AND m.org_id=s.org_id WHERE digest=? AND expires_at>? AND absolute_expiry>?", (hashlib.sha256(raw.encode()).hexdigest(), now(), now())).fetchone()
        if not row:
            raise HTTPException(401, "Session expired. Please sign in.")
        return dict(row)

    def public_session(s):
        with store.connect() as db:
            orgs = [dict(r) for r in db.execute("SELECT o.id,o.name,m.role FROM web_orgs o JOIN web_members m ON m.org_id=o.id WHERE m.user_id=?", (s["user_id"],))]
        return {"user": {"id": s["user_id"], "name": s["name"], "email": s["email"]}, "organization_id": s["org_id"], "role": s["role"], "organizations": orgs}

    def issue(response, request, user_id, org_id, absolute=None):
        raw = secrets.token_urlsafe(48)
        expiry = datetime.now(timezone.utc) + timedelta(hours=8)
        absolute = absolute or (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        with store.connect() as db:
            db.execute("INSERT INTO web_sessions VALUES(?,?,?,?,?)", (hashlib.sha256(raw.encode()).hexdigest(), user_id, org_id, min(expiry.isoformat(), absolute), absolute))
        response.set_cookie(COOKIE, raw, httponly=True, secure=request.url.scheme == "https", samesite="strict", max_age=8*3600, path="/api")

    def rate_limit(request, email):
        key = hashlib.sha256(f"{request.client.host if request.client else 'unknown'}:{email}".encode()).hexdigest()
        with store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            r = db.execute("SELECT * FROM web_login_attempts WHERE key=?", (key,)).fetchone()
            if r and r["reset_at"] > time.time() and r["count"] >= 15:
                raise HTTPException(429, "Too many attempts. Try again in 15 minutes.")
            count = r["count"] + 1 if r and r["reset_at"] > time.time() else 1
            reset = r["reset_at"] if r and r["reset_at"] > time.time() else time.time() + 900
            db.execute("INSERT OR REPLACE INTO web_login_attempts VALUES(?,?,?)", (key, count, reset))

    @router.post("/register", status_code=201)
    def register(body: Registration, request: Request, response: Response):
        rate_limit(request, body.email)
        if not body.terms:
            raise HTTPException(422, "Accept the workspace terms to continue")
        user_id, org_id = str(uuid4()), str(uuid4())
        hashed = password_hash(body.password)
        try:
            with store.connect() as db:
                db.execute("INSERT INTO web_users VALUES(?,?,?,?,?)", (user_id, body.email, body.name.strip(), hashed, now()))
                db.execute("INSERT INTO web_orgs VALUES(?,?)", (org_id, body.organization.strip()))
                db.execute("INSERT INTO web_members VALUES(?,?,'admin')", (user_id, org_id))
        except sqlite3.IntegrityError:
            raise HTTPException(409, "An account with this email already exists")
        issue(response, request, user_id, org_id)
        return {"created": True}

    @router.post("/login")
    def login(body: Credentials, request: Request, response: Response):
        rate_limit(request, body.email)
        with store.connect() as db:
            user = db.execute("SELECT * FROM web_users WHERE email=?", (body.email,)).fetchone()
            hashed = user["password_hash"] if user else password_hash("unused-password", "0"*32)
            valid = secrets.compare_digest(password_hash(body.password, hashed.split(":")[0]), hashed)
            if not user or not valid:
                raise HTTPException(401, "Email or password is incorrect")
            org = db.execute("SELECT org_id FROM web_members WHERE user_id=? ORDER BY org_id LIMIT 1", (user["id"],)).fetchone()
        issue(response, request, user["id"], org["org_id"])
        return {"authenticated": True}

    @router.get("/session")
    def get_session(s=Depends(session)):
        return public_session(s)

    @router.post("/refresh")
    def refresh(request: Request, response: Response, s=Depends(session)):
        with store.connect() as db:
            db.execute("DELETE FROM web_sessions WHERE digest=?", (s["digest"],))
        issue(response, request, s["user_id"], s["org_id"], s["absolute_expiry"])
        return public_session(s)

    @router.post("/logout")
    def logout(request: Request, response: Response):
        with store.connect() as db:
            db.execute("DELETE FROM web_sessions WHERE digest=?", (hashlib.sha256(request.cookies.get(COOKIE, "").encode()).hexdigest(),))
        response.delete_cookie(COOKIE, path="/api")
        return {"signed_out": True}

    @router.post("/organization/{org_id}")
    def switch(org_id: str, s=Depends(session)):
        with store.connect() as db:
            member = db.execute("SELECT role FROM web_members WHERE user_id=? AND org_id=?", (s["user_id"], org_id)).fetchone()
            if not member:
                raise HTTPException(403, "Organization membership required")
            db.execute("UPDATE web_sessions SET org_id=? WHERE digest=?", (org_id, s["digest"]))
        return {"organization_id": org_id}

    app.include_router(router)
    return session
