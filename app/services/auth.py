import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User

SECRET_KEY = os.getenv("SECRET_KEY", "change-this-in-production-use-a-long-random-string-min-32-chars")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 h

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# auto_error=False so unprotected routes still work without a token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


# -------------------------------------------------------
# Password helpers
# -------------------------------------------------------

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


# -------------------------------------------------------
# Token helpers
# -------------------------------------------------------

def create_access_token(user_id: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": user_id, "role": role, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


# -------------------------------------------------------
# FastAPI dependencies
# -------------------------------------------------------

def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Require a valid JWT. Raises 401 if absent or invalid."""
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = _decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    user = db.query(User).filter(User.user_id == payload.get("sub")).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or deactivated")
    return user


def get_optional_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Return the user if a valid token is present, otherwise None."""
    if not token:
        return None
    payload = _decode_token(token)
    if not payload:
        return None
    return db.query(User).filter(User.user_id == payload.get("sub")).first()


def scope_query_to_owner(query, owner_column, current_user: Optional[User]):
    """
    Restrict a SQLAlchemy query so each user only sees rows they own.

    - Authenticated users see rows where owner_column == their user_id.
    - Unauthenticated requests see rows where owner_column IS NULL
      (preserves anonymous usage for legacy/test clients).

    Always call this on any query that returns user-owned data so no user
    can read another user's records.
    """
    if current_user is not None:
        return query.filter(owner_column == current_user.user_id)
    return query.filter(owner_column.is_(None))


def user_owns_record(current_user: Optional[User], owner_id: Optional[str]) -> bool:
    """
    Return True if *current_user* is allowed to act on a record whose
    owner_id is *owner_id*, using the same rule as `scope_query_to_owner`.
    """
    if current_user is not None:
        return owner_id == current_user.user_id
    return owner_id is None


def require_roles(*roles: str):
    """Dependency factory: require the current user to have one of the given roles."""
    def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires one of the following roles: {', '.join(roles)}"
            )
        return current_user
    return _check
