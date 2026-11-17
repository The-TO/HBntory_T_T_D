"""
Script d'initialisation de la base de données HBntory.

Crée :
- les tables ;
- deux branches ;
- un administrateur ;
- un stock d'exemple.

Le mot de passe administrateur peut être défini avec la variable
d'environnement HBNTORY_ADMIN_PASSWORD.
"""

import os
from datetime import datetime, timezone

from db import db, init_db
from models import Branch, Stock, User


ADMIN_USERNAME = "admin"
ADMIN_EMAIL = "admin@hbntory.local"
ADMIN_ROLE = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"

BRANCHES = [
    {
        "id": 1,
        "name": "Main Campus",
        "address": "12 Main Street",
    },
    {
        "id": 2,
        "name": "North Campus",
        "address": "48 North Avenue",
    },
]

SAMPLE_STOCK = [
    {"product_id": 1, "branch_id": 1, "quantity": 12},
    {"product_id": 2, "branch_id": 1, "quantity": 8},
    {"product_id": 3, "branch_id": 1, "quantity": 15},
    {"product_id": 5, "branch_id": 1, "quantity": 25},
    {"product_id": 6, "branch_id": 1, "quantity": 30},
    {"product_id": 9, "branch_id": 1, "quantity": 10},
    {"product_id": 12, "branch_id": 1, "quantity": 6},
    {"product_id": 15, "branch_id": 1, "quantity": 18},
    {"product_id": 1, "branch_id": 2, "quantity": 7},
    {"product_id": 3, "branch_id": 2, "quantity": 9},
    {"product_id": 5, "branch_id": 2, "quantity": 14},
    {"product_id": 6, "branch_id": 2, "quantity": 20},
    {"product_id": 9, "branch_id": 2, "quantity": 5},
    {"product_id": 12, "branch_id": 2, "quantity": 4},
    {"product_id": 15, "branch_id": 2, "quantity": 11},
]


def utc_now():
    """Retourne la date et l'heure actuelles en UTC."""
    return datetime.now(timezone.utc)


def create_app():
    """Crée une application Flask minimale pour initialiser la base."""
    app = Flask(__name__)

    project_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..")
    )

    data_dir = os.path.join(project_root, "data")
    os.makedirs(data_dir, exist_ok=True)

    database_path = os.path.join(data_dir, "hbntory.db")
    database_url = f"sqlite:///{database_path}"

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    init_db(app)

    return app


def create_admin():
    """Crée l'administrateur initial."""
    admin_password = os.environ.get(
        "HBNTORY_ADMIN_PASSWORD",
        DEFAULT_ADMIN_PASSWORD,
    )

    existing_admin = User.query.filter_by(
        username=ADMIN_USERNAME
    ).first()

    if existing_admin:
        print("L'administrateur existe déjà.")
        return

    admin = User(
        username=ADMIN_USERNAME,
        email=ADMIN_EMAIL,
        password=admin_password,
        role=ADMIN_ROLE,
        is_active=True,
        created_at=utc_now(),
    )

    db.session.add(admin)
    db.session.commit()

    print("Administrateur créé.")


def create_branches():
    """Crée les branches initiales."""
    for branch_data in BRANCHES:
        existing_branch = Branch.query.filter_by(
            id=branch_data["id"]
        ).first()

        if existing_branch:
            print(f"La branche '{branch_data['name']}' existe déjà.")
            continue

        branch = Branch(
            id=branch_data["id"],
            name=branch_data["name"],
            address=branch_data["address"],
        )

        db.session.add(branch)

    db.session.commit()
    print("Branches initialisées.")


def create_sample_stock():
    """Crée un stock d'exemple pour tester l'application."""
    if Stock.query.count() > 0:
        print("Le stock contient déjà des données.")
        return

    for stock_data in SAMPLE_STOCK:
        stock = Stock(
            product_id=stock_data["product_id"],
            branch_id=stock_data["branch_id"],
            quantity=stock_data["quantity"],
            updated_at=utc_now(),
        )

        db.session.add(stock)

    db.session.commit()
    print(f"{len(SAMPLE_STOCK)} entrées de stock créées.")


def main():
    """Point d'entrée du script d'initialisation."""
    app = create_app()

    with app.app_context():
        db.create_all()

        create_branches()
        create_admin()
        create_sample_stock()

    print("Initialisation de la base terminée.")


if __name__ == "__main__":
    main()
