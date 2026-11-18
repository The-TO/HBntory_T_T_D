"""Helpers for retrieving the current user and enforcing access requirements."""

from flask import abort, request
import auth
SESSION_COOKIE = "session_token"

def get_current_user():
    """Return the current user based on the request's session cookie.
    """
    return auth.get_current_user(request.cookies.get(SESSION_COOKIE))


def require_login():
    """Require an authenticated user.
    """
    user = get_current_user()
    if user is None:
        abort(401)
    return user


def require_role(role):
    """Require the current user to have the specified role.
    """
    user = require_login()
    if user.role != role:
        abort(403)
    return user


def current_branch_id():
    """Return the branch ID for the current common-role user.
    """
    return require_role("common").branch_id
