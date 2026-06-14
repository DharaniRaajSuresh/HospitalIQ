"""Auth endpoints: login, register, me, logout — httpOnly cookie-based JWT."""
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from backend.auth import (clear_token_cookie, create_access_token,
                           get_current_user, get_password_hash,
                           set_token_cookie, verify_password)
from backend.database import get_db
from backend.models import User

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Auth"], prefix="/api/v1/auth")


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str = ""


@router.post("/login")
async def login(request: LoginRequest, response: Response, db=Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token({"sub": user.email, "role": user.role})
    set_token_cookie(response, token)
    return {"access_token": token, "token_type": "bearer",
            "user": {"email": user.email, "name": user.full_name, "role": user.role}}


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
    token = create_access_token({"sub": user.email, "role": user.role})
    set_token_cookie(response, token)
    return {"access_token": token, "token_type": "bearer",
            "user": {"email": user.email, "name": user.full_name, "role": user.role}}


@router.post("/logout")
async def logout(response: Response):
    clear_token_cookie(response)
    return {"status": "ok"}


@router.get("/me")
async def get_me(request: Request, user=Depends(get_current_user)):
    if user is None:
        return {"authenticated": False}
    return {"authenticated": True, "email": user.email, "name": user.full_name, "role": user.role}
