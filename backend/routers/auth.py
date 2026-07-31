"""Auth endpoints: login, register, me, logout, Google OAuth — httpOnly cookie-based JWT."""
import logging
import os
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from backend.auth import (
    clear_token_cookie,
    create_access_token,
    get_current_user,
    get_password_hash,
    set_token_cookie,
    verify_password,
)
from backend.config import settings
from backend.database import get_db
from backend.models import User

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Auth"], prefix="/api/v1/auth")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8510")


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str = ""


def _make_user_response(user: User, response: Response) -> dict:
    token = create_access_token({"sub": user.email, "role": user.role})
    set_token_cookie(response, token)
    return {"access_token": token, "token_type": "bearer",
            "user": {"email": user.email, "name": user.full_name, "role": user.role, "avatar": user.avatar_url}}


@router.post("/login")
async def login(request: LoginRequest, response: Response, db=Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not user.hashed_password or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return _make_user_response(user, response)


@router.post("/register")
async def register(request: RegisterRequest, response: Response, db=Depends(get_db)):
    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=request.email, hashed_password=get_password_hash(request.password),
                full_name=request.full_name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return _make_user_response(user, response)


class SetPasswordRequest(BaseModel):
    password: str


@router.post("/set-password")
async def set_password(request: SetPasswordRequest, response: Response, user=Depends(get_current_user), db=Depends(get_db)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user.hashed_password = get_password_hash(request.password)
    db.commit()
    return {"status": "ok", "message": "Password set successfully"}


@router.post("/logout")
async def logout(response: Response):
    clear_token_cookie(response)
    return {"status": "ok"}


@router.get("/me")
async def get_me(request: Request, user=Depends(get_current_user)):
    if user is None:
        return {"authenticated": False}
    return {"authenticated": True, "email": user.email, "name": user.full_name,
            "role": user.role, "avatar": user.avatar_url}


@router.get("/google/login")
async def google_login(request: Request):
    if not settings.google_client_id:
        raise HTTPException(status_code=501, detail="Google OAuth not configured — set GOOGLE_CLIENT_ID in .env")
    state = secrets.token_urlsafe(32)
    request.session["google_oauth_state"] = state
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }
    redirect_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    logger.info("Google login redirect: %s", redirect_url[:80])
    return RedirectResponse(url=redirect_url)


@router.get("/google/callback")
async def google_callback(request: Request, db=Depends(get_db)):
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    stored_state = request.session.pop("google_oauth_state", None)

    if not code:
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=no_code")
    if not stored_state or state != stored_state:
        logger.warning("Google OAuth state mismatch: got=%s expected=%s", state, stored_state)
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=state_mismatch")

    # Exchange authorization code for tokens
    try:
        async with httpx.AsyncClient() as client:
            token_resp = await client.post(GOOGLE_TOKEN_URL, data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            })
            token_data = token_resp.json()
            logger.info("Google token exchange status=%s", token_resp.status_code)
            if token_resp.status_code != 200:
                logger.error("Token exchange failed: %s", token_data)
                return RedirectResponse(url=f"{FRONTEND_URL}/login?error=token_exchange")
    except Exception:
        logger.error("Token exchange HTTP error: %s", exc_info=True)
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=token_exchange")

    # Fetch userinfo with the access token
    access_token = token_data.get("access_token")
    if not access_token:
        logger.error("No access_token in response")
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=no_token")

    try:
        async with httpx.AsyncClient() as client:
            userinfo_resp = await client.get(GOOGLE_USERINFO_URL, headers={
                "Authorization": f"Bearer {access_token}"
            })
            userinfo = userinfo_resp.json()
            logger.info("Google userinfo status=%s", userinfo_resp.status_code)
            if userinfo_resp.status_code != 200:
                logger.error("Userinfo fetch failed: %s", userinfo)
                return RedirectResponse(url=f"{FRONTEND_URL}/login?error=userinfo_failed")
    except Exception:
        logger.error("Userinfo fetch HTTP error", exc_info=True)
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=userinfo_failed")

    email = userinfo.get("email")
    if not email:
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=no_email")

    google_id = userinfo.get("sub")
    name = userinfo.get("name", email.split("@")[0])
    avatar = userinfo.get("picture", "")

    user = db.query(User).filter(
        (User.email == email) | (User.google_id == google_id)
    ).first()
    if user:
        if not user.google_id:
            user.google_id = google_id
            user.avatar_url = avatar
    else:
        user = User(email=email, google_id=google_id, full_name=name,
                    avatar_url=avatar, hashed_password=None)
        db.add(user)
    db.commit()
    db.refresh(user)

    jwt_token = create_access_token({"sub": user.email, "role": user.role})
    resp = RedirectResponse(url=f"{FRONTEND_URL}/login?token={jwt_token}")
    set_token_cookie(resp, jwt_token)
    return resp
