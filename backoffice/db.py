"""Connection à la base de données avec SQLAlchemy."""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker


import config


engine = create_engine(config.DATABASE_URL)


@event.listen_for(engine, "connect")

def enable_foreign_keys(dbapi_connection, connection_record):
    """SQLite ne verifie les clés etrangeres que si in le lui demande."""
    if config.DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

#scoped_session : chaque requete web obtien sa propre session.
db_session = scoped_session(sessionmaker(bind=engine))


Base = declarative_base()