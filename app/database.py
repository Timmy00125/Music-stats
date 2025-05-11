from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from app.config import settings

# Create the SQLAlchemy engine
engine = create_engine(
    str(settings.DATABASE_URL),
    pool_size=5,
    max_overflow=10,
    poolclass=QueuePool,
    pool_pre_ping=True,
)

# Create a SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a Base class for declarative models
Base = declarative_base()


# Dependency to get DB session
def get_db():
    """
    Dependency to get database session.
    Yields a SQLAlchemy session and ensures it's closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
