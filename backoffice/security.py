"""hachage et verification des mots de passe avec bcrypt"""

import bcrypt

def hash_password(password):
    """Transforme un mot de passe en hash bcrupt (texte à stocker)"""

    salt = bcrypt.gensalt()   #sel aléatoire, différent à chaque appel

    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)

    return hashed.decode("utf-8")


def verify_password(password, password_hash):
    """renvoie True si le mot de passe correspond au hash stocké."""
    return bcrypt.checkpw(
        password.encode("utf-8"), password_hash.encode("utf-8")
    )