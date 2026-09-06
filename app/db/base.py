"""Base declarativa compartida por los modelos SQLAlchemy."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base de los modelos persistidos."""
