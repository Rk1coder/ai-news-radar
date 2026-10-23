from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ai_news_radar.config import DATABASE_URL
from ai_news_radar.models import Base

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def init_db() -> None:
    Base.metadata.create_all(engine)


def get_session() -> Session:
    return SessionLocal()
