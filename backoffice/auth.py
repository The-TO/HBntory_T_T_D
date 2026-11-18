"""Authentification du Backoffice (sans framework web) : login, session, protection."""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from db import db_session
from models import User, UserSession
from security import hash_password, verify_password

SESSION_DURATION = timedelta(hours=8)

# Hash factice : même travail bcrypt quand l'utilisateur n'existe pas,
# pour ne pas révéler l'existence d'un compte par le temps de réponse.
_DUMMY_HASH = hash_password("not-a-real-password")


class AuthError(Exception):
    """Erreur d'authentification (le message est affichable)."""


class InvalidCredentials(AuthError):
    """Identifiants incorrects, compte inexistant ou supprimé."""


class NotAuthenticated(AuthError):
    """Jeton absent, inconnu, expiré, ou compte supprimé depuis."""


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def authenticate(username, password):
    """Renvoie l'utilisateur si les identifiants sont valides, sinon None.

    Les utilisateurs supprimés (deleted_at renseigné) sont rejetés.
    """
    user = (
        db_session.query(User)
        .filter(User.username == (username or "").strip(), User.deleted_at.is_(None))
        .first()
    )
    if user is None:
        verify_password(password or "", _DUMMY_HASH)
        return None
    if not verify_password(password or "", user.password_hash):
        return None
    return user


def login(username, password):
    """Vérifie les identifiants et renvoie un jeton de session."""
    user = authenticate(username, password)
    if user is None:
        # Message générique : ne dit pas si le compte existe ou est supprimé.
        raise InvalidCredentials("Invalid username or password.")

    token = secrets.token_urlsafe(32)  # 256 bits aléatoires
    now = _now()
    db_session.add(
        UserSession(
            token_hash=_hash_token(token),
            user_id=user.id,
            created_at=now,
            expires_at=now + SESSION_DURATION,
        )
    )
    db_session.commit()
    return token


def get_current_user(token):
    """Renvoie l'utilisateur lié au jeton, ou None si le jeton n'est pas valable.

    Re-vérifie en base à chaque appel : jeton connu, non expiré,
    et utilisateur non supprimé.
    """
    if not token:
        return None
    return (
        db_session.query(User)
        .join(UserSession, UserSession.user_id == User.id)
        .filter(
            UserSession.token_hash == _hash_token(token),
            UserSession.expires_at > _now(),
            User.deleted_at.is_(None),
        )
        .first()
    )


def require_user(token):
    """Comme get_current_user, mais lève NotAuthenticated si pas authentifié."""
    user = get_current_user(token)
    if user is None:
        raise NotAuthenticated("Authentication required.")
    return user


def logout(token):
    """Détruit la session : le jeton devient inutilisable immédiatement."""
    db_session.query(UserSession).filter(
        UserSession.token_hash == _hash_token(token or "")
    ).delete()
    db_session.commit()
