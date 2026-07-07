from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.user import User
from app.schemas.user import UserCreate
from app.services.exceptions import DuplicateUserError


class UserService:
    def __init__(self, db: Session):
        self.db = db

    def get_by_email(self, email: str) -> Optional[User]:
        statement = select(User).where(func.lower(User.email) == email.lower())
        return self.db.execute(statement).scalar_one_or_none()

    def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        statement = select(User).where(User.id == user_id)
        return self.db.execute(statement).scalar_one_or_none()

    def create_user(self, user_in: UserCreate) -> User:
        email = user_in.email.lower()
        phone_number = user_in.phone_number

        duplicate_filters = [func.lower(User.email) == email]
        if phone_number:
            duplicate_filters.append(User.phone_number == phone_number)

        duplicate = self.db.execute(
            select(User.id).where(or_(*duplicate_filters))
        ).scalar_one_or_none()
        if duplicate:
            raise DuplicateUserError

        user = User(
            email=email,
            phone_number=phone_number,
            full_name=user_in.full_name,
            preferred_language=user_in.preferred_language,
            hashed_password=get_password_hash(user_in.password),
        )

        self.db.add(user)
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise DuplicateUserError from exc

        self.db.refresh(user)
        return user
