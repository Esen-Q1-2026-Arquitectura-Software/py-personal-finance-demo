import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://financeuser:financepass@localhost:3306/finance",
)

# pool_pre_ping=True reconnects automatically after a MySQL "gone away" error
# connect_args timeout is in seconds (PyMySQL kwarg)
# Docs: https://pymysql.readthedocs.io/en/latest/modules/connections.html
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 10},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


# FastAPI dependency – yields a DB session and closes it when the request ends
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
