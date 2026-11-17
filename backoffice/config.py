"""Tout les Reglages du backoffice au meme endroit, lus depuis les variables d'environnement."""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "..", "data", "hbntory.db")

#__file__ = chemin du fichier config.py
# os.path.abspath(...) = le transforme en chemin complet, par exemple /user/theo/hntory/.../config.py
#os.path.dirname = retiens que le dossier 
#os.path.join(BASE_DIR, "..", "data", "hbntory.db") = remonte d'un dossier(..) puis descend dans data/ : Users/.../hbntory.db



# Adresse de la base de données (SQLite par defaut : un simple fichier).

DATABASE_URL = os.environ.get(
    "DATABASE_URL"
)