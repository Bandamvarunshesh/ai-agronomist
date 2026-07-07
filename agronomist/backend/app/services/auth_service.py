from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.security import create_access_token, verify_password
from app.schemas.auth import Token
from app.schemas.user import UserLogin
from app.services.exceptions import InactiveUserError, InvalidCredentialsError
from app.services.user_service import UserService


class AuthService:
    def __init__(self, db: Session):
        self.user_service = UserService(db)

    def login(self, credentials: UserLogin) -> Token:
        user = self.user_service.get_by_email(credentials.email)
        if user is None or not verify_password(
            credentials.password,
            user.hashed_password,
        ):
            raise InvalidCredentialsError

        if not user.is_active:
            raise InactiveUserError

        return Token(access_token=create_access_token(str(user.id)))
