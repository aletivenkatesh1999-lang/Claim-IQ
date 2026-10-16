from fastapi import Depends, HTTPException, status

from .auth import get_current_user
from .models import User, UserRole


def require_roles(
    *allowed_roles: UserRole
):

    def role_checker(
        current_user: User = Depends(
            get_current_user
        )
    ) -> User:

        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )

        return current_user

    return role_checker


admin_only = require_roles(
    UserRole.admin
)


officer_or_admin = require_roles(
    UserRole.admin,
    UserRole.claim_officer
)