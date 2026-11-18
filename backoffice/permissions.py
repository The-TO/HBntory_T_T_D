from flask import abort
from auth import get_current_user

def require_login():
    user = get_current_user()
    if user is None:
        abort(401)
    return user

def require_role(role):
    user = require_login()
    if user.role != role:
        abort(403)
    return user

def current_branch_id():
    return require_role("common").branch_id
