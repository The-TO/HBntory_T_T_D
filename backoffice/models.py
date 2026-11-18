"""SQLAlchemy models for branches, users, and branch stock inventory."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)

from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Branch(Base):
    """Represent a branch and its related users and stock items."""

    __tablename__= "branches"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    users = relationship("User", back_populates="branch")
    stock_items = relationship("Stock", back_populates="branch")


class User(Base):
    """Represent a user and, when applicable, their assigned branch."""

    __tablename__= "users"
    # Verify that the common user can have a branch but not the admin
    __table_args__ = (
        CheckConstraint(
            "(role = 'admin' AND branch_id IS NULL) "
            "OR (role = 'common' AND branch_id IS NOT NULL)",
            name="ck_users_role_branch",
        ),
    )

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(10), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    branch = relationship("Branch", back_populates="users")


class Stock(Base):
    """Represent a product's quantity at a branch."""

    __tablename__= "stock"
    # Check if the branch_id and product_id are unique, and if the quantity isn't negative
    __table_args__ = (
        UniqueConstraint("branch_id", "product_id", name="uq_stock_branch_product"),
        CheckConstraint("quantity >= 0", name="ck_stock_quantity_non_negative"),
    )

    id = Column(Integer, primary_key=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    product_id = Column(String(64), nullable=False)
    quantity = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    branch = relationship("Branch", back_populates="stock_items")
