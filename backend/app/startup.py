from .database import engine, Base


def create_tables():
    """Create database tables."""
    Base.metadata.create_all(bind=engine)


def startup_event():
    """Application startup event handler."""
    create_tables()