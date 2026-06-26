"""
WHAT THIS FILE DOES:
Handles DATABASE QUERIES for user accounts (login, registration).
Currently provides basic user lookup by email. Used for authentication
features (not yet the main focus — the dashboard is open-access for now).

UserRepository - Concrete repository for user accounts
Demonstrates: Inheritance, Polymorphism
"""

import logging
from typing import Any

from sqlalchemy.orm import Session

from backend.core.base_repository import BaseRepository
from backend.models import User

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository):
    """
    Concrete repository for User table.
    
    OOP Principles:
    - Inheritance: extends BaseRepository
    - Polymorphism: user-specific queries
    """

    def __init__(self, db: Session):
        super().__init__(db, User)

    def get_by_email(self, email: str) -> User | None:
        """Get user by email address."""
        return self._db.query(User).filter(User.email == email).first()

    def get_by_state(self, state: str) -> list[User]:
        raise NotImplementedError("Users do not have a state field")

    def get_summary_stats(self) -> dict[str, Any]:
        """Get user statistics."""
        active_count = self._db.query(User).filter(User.is_active == True).count()
        total_count = self.count()
        return {
            "total_users": total_count,
            "active_users": active_count,
            "inactive_users": total_count - active_count
        }

    def get_active_users(self) -> list[User]:
        """Get all active users."""
        return self._db.query(User).filter(User.is_active == True).all()

    def get_by_role(self, role: str) -> list[User]:
        """Get users by role."""
        return self._db.query(User).filter(User.role == role).all()

    def deactivate_user(self, user_id: int) -> bool:
        """Deactivate a user account."""
        user = self.get_by_id(user_id)
        if user:
            user.is_active = False
            self._db.commit()
            return True
        return False

    def activate_user(self, user_id: int) -> bool:
        """Activate a user account."""
        user = self.get_by_id(user_id)
        if user:
            user.is_active = True
            self._db.commit()
            return True
        return False
