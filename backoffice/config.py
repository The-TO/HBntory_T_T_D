"""tout les Réglages du Backoffice en un seul endroit, lus depuis les variables d'environnement."""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "..", "data", "hbntory.db")

# SQLite ne crée pas le dossier : on s'assure qu'il existe.
os.makedirs(os.path.dirname(os.path.abspath(DEFAULT_DB_PATH)), exist_ok=True)

# Adresse de la base de données (SQLite par défaut : un simple fichier).
DATABASE_URL = os.environ.get(
    "DATABASE_URL", "sqlite:///" + os.path.abspath(DEFAULT_DB_PATH)
)

# Adresse de la Product API fournie (conteneur Docker, port 5001).
PRODUCT_API_URL = os.environ.get("PRODUCT_API_URL", "http://localhost:5001")

# Clé qui signe le cookie de session.
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")

# Mot de passe de l'admin créé par init_db.py (jamais stocké en clair).
ADMIN_PASSWORD = os.environ.get("HBNTORY_ADMIN_PASSWORD")
