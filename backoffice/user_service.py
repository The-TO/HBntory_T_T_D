"""Règles métier des utilisateurs (réservées à l'admin)

Provides business rules for creating, updating, listing, and soft-deleting
users. These operations are intended for administrators.
"""

from db import db_session
from models import Branch, User, ROLE_COMMON
from security import hash_password
from datetime import datetime, timezone

MIN_PASSWORD_LENGTH = 8


class UserError(Exception):
    """Represents a user operation that was rejected with a displayable message.
    """


def _check_password(password):
    """Validate that a password meets the minimum length requirement.
    """
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        raise UserError(
            "Password must be at least %d characters" %MIN_PASSWORD_LENGTH
        )


def _check_branch(branch_id):
    """Retrieve a branch by its identifier.
    """
    try:
        branch = db_session.get(Branch, int(branch_id))
    except (TypeError, ValueError):
        branch = None
    if branch is None:
        raise UserError("Please choose a valid branch")
    return branch


def get_common_user(user_id):
    """Retrieve an existing, undeleted user who is not an administrator.
    """
    user =db_session.get(User, user_id)
    if user is None or user.is_admin or user.is_deleted:
        raise UserError ("User not found")
    return user


def list_users():
    """Return all users ordered by username.
    """
    return db_session.query(User).order_by(User.username).all()


def create_user(username, password, branch_id):
    """Create a common user after validating its details.
    """
    username = (username or "").strip()
    if not username:
        raise UserError("username is required")
    if db_session.query(User).filter_by(username=username).first(): #verifie que aucun utilisateur possede deja le nom
        raise UserError("this username is already taken")
    _check_password(password)
    branch = _check_branch(branch_id)
    user = User(username=username, role=ROLE_COMMON, branch_id=branch.id,
                password_hash=hash_password(password))
    db_session.add(user)
    db_session.commit()
    return user


def update_user(user_id, branch_id, new_password=""):
    """Update a common user's branch and optionally its password.
    """
    user = get_common_user(user_id)
    user.branch_id = _check_branch(branch_id).id
    if new_password:  # champ vide = on garde l'ancien mot de passe
        _check_password(new_password)
        user.password_hash = hash_password(new_password)
    db_session.commit()
    return user


def soft_delete_user(user_id):
    """Mark a common user's account as deleted without removing its database row.
    """
    user = get_common_user(user_id)
    user.deleted_at = datetime.now(timezone.utc)
    db_session.commit()
    return user
