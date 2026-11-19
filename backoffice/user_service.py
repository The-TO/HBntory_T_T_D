"""Règles métier des utilisateurs (réservées à l'admin)"""

from db import db_session
from models import Branch, User, ROLE_COMMON, func
from security import hash_password

MIN_PASSWORD_LENGTH = 8


class UserError(Exception):
    """Opération sur un utilisateur refusée(message affichable)"""

def _check_password(password):
    """Verifie la longueur du mot de passe"""
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        raise UserError(
            "Password must be at least %d characters" %MIN_PASSWORD_LENGTH
        )


def _check_branch(branch_id):
    """verifie que la succursale existe """
    try:
        branch = db_session.get(Branch, int(branch_id))
    except (TypeError, ValueError):
        branch = None
    if branch is None:
        raise UserError("Please choose a valid branch")
    return branch

def get_common_user(user_id):
    """Empeche la modification d'un'admin ni d'un compte déja supprimé"""
    user =db_session.get(User, user_id)
    if user is None or user.is_admin or user.is_deleted:
        raise UserError ("User not found")
    return user


def list_users():
    """Renvoi la liste des utilisateurs, dans l'odre croissant des noms"""
    return db_session.query(User).order_by(User.username).all()

def create_user(username, password, branch_id):
    username = (username or "").strip()
    if not username:
        raise UserError("username is required")
    if db_session.query(User).filter_by(username=username).first(): #verifie que aucun utilisateur possede deja le nom
        raise UserError("this username is already taken")
    _check_password(password)
    branch = _check_branch(branch_id)
    user = User(username=username, role=ROLE_COMMON, branch.id=branch.id,
                password_hash=hash_password(password))
    db_session.add(user)
    db_session.commit()
    return user

def update_user(user_id, branch_id, new_password=""):
    user = _get_common_user(user_id)
    user.branch_id = _check_branch(branch_id).id
    if new_password:  # champ vide = on garde l'ancien mot de passe
        _check_password(new_password)
        user.password_hash = hash_password(new_password)
    db_session.commit()
    return user


def soft_delete_user(user_id):
    """Marque le compte comme supprimé. Aucune ligne n'est effacée."""
    user = get_common_user(user_id)
    user.deleted_at = func.now
    db_session.commit()
    return user