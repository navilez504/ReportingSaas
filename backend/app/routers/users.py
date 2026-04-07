from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.user import UserOut, UserUpdate
from app.services.admin_bootstrap import ensure_config_admin_user
from app.services.user import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def me(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    repo = UserRepository(db)
    current = ensure_config_admin_user(current, repo, get_settings())
    return UserOut.model_validate(current)


@router.patch("/me", response_model=UserOut)
def update_me(
    data: UserUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    repo = UserRepository(db)
    svc = UserService(repo)
    return svc.update_profile(current.id, data)
