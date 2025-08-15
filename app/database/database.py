from sqlmodel import SQLModel, Session, create_engine
from contextlib import contextmanager
from .config import get_settings
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

engine = create_engine(url=get_settings().DATABASE_URL_psycopg, echo=True, pool_size=5, max_overflow=10)


def get_session():
    with Session(engine) as session:
        yield session

def init_db():
    # Исправлено: создаём таблицы только если их нет, не удаляем существующие данные
    SQLModel.metadata.create_all(engine)