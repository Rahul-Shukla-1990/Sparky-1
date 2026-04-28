from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import User
from app.schemas import LoginRequest, UserOut, UserCreate
from app.security import verify_password, create_session_token, hash_password
from app.deps import get_current_user, require_role
from app.audit import write_audit

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/login")
def login(payload: LoginRequest, response: Response, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    user.last_login_at = datetime.now(timezone.utc); db.commit()
    response.set_cookie("mosint_session", create_session_token(user.id, user.username, user.role), httponly=True, samesite="lax", secure=False, max_age=12*3600)
    write_audit(db, user, "login", "user", str(user.id), "User logged in", request.client.host if request.client else None)
    return {"status": "ok", "user": UserOut.model_validate(user)}

@router.post("/logout")
def logout(response: Response, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    response.delete_cookie("mosint_session")
    write_audit(db, user, "logout", "user", str(user.id), "User logged out", request.client.host if request.client else None)
    return {"status": "ok"}

@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user

@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), user: User = Depends(require_role("Admin"))):
    return db.query(User).order_by(User.username.asc()).all()

@router.post("/users", response_model=UserOut)
def create_user(payload: UserCreate, request: Request, db: Session = Depends(get_db), user: User = Depends(require_role("Admin"))):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    nu = User(username=payload.username, display_name=payload.display_name, role=payload.role, password_hash=hash_password(payload.password), is_active=True)
    db.add(nu); db.commit(); db.refresh(nu)
    write_audit(db, user, "create_user", "user", str(nu.id), f"Created user {nu.username} role={nu.role}", request.client.host if request.client else None)
    return nu
