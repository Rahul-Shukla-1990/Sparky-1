from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import User
from app.security import read_session_token, role_at_least


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("mosint_session")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = read_session_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    user = db.query(User).filter(User.id == payload.get("uid")).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User inactive or not found")
    return user


def require_role(required_role: str):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if not role_at_least(user.role, required_role):
            raise HTTPException(status_code=403, detail=f"{required_role} role required")
        return user
    return dependency
