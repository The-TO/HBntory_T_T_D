"""
Initialize the HBntory database.

Creates:
- the tables (from models.py);
- two branches;
- the admin user (password hashed with bcrypt);
- sample stock, built from the real products of the Product API.

The script can be run several times: existing rows are not duplicated.

Usage (from the backoffice/ folder):
    HBNTORY_ADMIN_PASSWORD='choose-a-password' python init_db.py

The admin password is never written in the code: it is read from the
HBNTORY_ADMIN_PASSWORD environment variable and only its bcrypt hash is saved.
"""

import os
import sys

import bcrypt
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

import config
import product_client
from models import Base, Branch, Stock, User

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_ENV = "HBNTORY_ADMIN_PASSWORD"

BRANCH_NAMES = ["Main Campus", "North Campus"]

# Quantity per product, in the order returned by the Product API.
# None = the branch does not hold this product (availability differs per branch).
SAMPLE_QUANTITIES = {
    "Main Campus": [12, 8, 15, 25, 30, 10, 6, 18],
    "North Campus": [7, None, 9, 14, 20, None, 5, 11],
}


def make_engine():
    """Create the SQLAlchemy engine (SQLite file by default)."""
    if config.DATABASE_URL:
        url = config.DATABASE_URL
    else:
        db_path = os.path.abspath(config.DEFAULT_DB_PATH)
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        url = "sqlite:///" + db_path

    engine = create_engine(url)

    if engine.dialect.name == "sqlite":
        # SQLite ignores foreign keys unless this is enabled on each connection.
        @event.listens_for(engine, "connect")
        def enable_foreign_keys(dbapi_connection, _record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def hash_password(password):
    """Return the bcrypt hash of a password (salt included in the hash)."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def create_branches(session):
    """Create the initial branches and return them by name."""
    branches = {}

    for name in BRANCH_NAMES:
        branch = session.query(Branch).filter_by(name=name).first()
        if branch is None:
            branch = Branch(name=name)
            session.add(branch)
            print(f"Branch created: {name}")
        else:
            print(f"Branch already exists: {name}")
        branches[name] = branch

    session.commit()
    return branches


def create_admin(session):
    """Create the admin user (no branch) if it does not exist yet."""
    if session.query(User).filter_by(username=ADMIN_USERNAME).first():
        print("Admin already exists.")
        return

    password = os.environ.get(ADMIN_PASSWORD_ENV)
    if not password:
        sys.exit(
            f"Admin not created: set the {ADMIN_PASSWORD_ENV} environment "
            "variable and run this script again."
        )

    admin = User(
        username=ADMIN_USERNAME,
        password_hash=hash_password(password),
        role="admin",
        branch_id=None,
    )
    session.add(admin)
    session.commit()
    print("Admin created.")


def create_sample_stock(session, branches):
    """Create sample stock using the real SKUs of the Product API."""
    try:
        products = product_client.list_products()
    except product_client.ProductAPIError as error:
        print(
            f"Sample stock skipped: Product API unavailable ({error}). "
            "Start the Product API and run this script again."
        )
        return

    skus = [product["sku"] for product in products]
    if not skus:
        print("Sample stock skipped: the Product API returned no products.")
        return

    created = 0
    for branch_name, quantities in SAMPLE_QUANTITIES.items():
        branch = branches[branch_name]
        for sku, quantity in zip(skus, quantities):
            if quantity is None:
                continue
            existing = (
                session.query(Stock)
                .filter_by(branch_id=branch.id, product_id=sku)
                .first()
            )
            if existing:
                continue
            session.add(Stock(branch_id=branch.id, product_id=sku, quantity=quantity))
            created += 1

    session.commit()
    print(f"Sample stock: {created} line(s) created.")


def main():
    """Entry point of the initialization script."""
    engine = make_engine()
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        branches = create_branches(session)
        create_admin(session)
        create_sample_stock(session, branches)

    print("Database initialization finished.")


if __name__ == "__main__":
    main()
