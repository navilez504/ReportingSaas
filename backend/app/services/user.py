from app.repositories.user import UserRepository
from app.schemas.user import UserOut, UserUpdate


class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    def me(self, user_id: int) -> UserOut:
        user = self.repo.get_by_id(user_id)
        assert user is not None
        return UserOut.model_validate(user)

    def update_profile(self, user_id: int, data: UserUpdate) -> UserOut:
        user = self.repo.get_by_id(user_id)
        assert user is not None
        user = self.repo.update(user, data.full_name)
        return UserOut.model_validate(user)
