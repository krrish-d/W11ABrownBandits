from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserResponse, TokenResponse
from app.services.auth import (
    verify_password,
    hash_password,
    create_access_token,
    get_current_user,
    require_roles,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# -------------------------------------------------------
# POST /auth/signup
# -------------------------------------------------------
@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.user_id, user.role)
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


# -------------------------------------------------------
# POST /auth/login   (also accepts OAuth2 form for /docs)
# -------------------------------------------------------
@router.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")

    token = create_access_token(user.user_id, user.role)
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


# -------------------------------------------------------
# GET /auth/me
# -------------------------------------------------------
@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user


# -------------------------------------------------------
# PUT /auth/me  (update own profile)
# -------------------------------------------------------
@router.put("/me", response_model=UserResponse)
def update_me(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    update_data = payload.model_dump(exclude_unset=True)
    # Regular users cannot elevate their own role
    if "role" in update_data and current_user.role != "admin":
        update_data.pop("role")
    for field, value in update_data.items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user


# -------------------------------------------------------
# GET /auth/users  (admin only)
# -------------------------------------------------------
@router.get("/users", response_model=list[UserResponse])
def list_users(
    _admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    return db.query(User).all()


# -------------------------------------------------------
# PUT /auth/users/{user_id}  (admin only – manage other users)
# -------------------------------------------------------
@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: str,
    payload: UserUpdate,
    _admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user
