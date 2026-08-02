"""
Engine e sessão do SQLAlchemy (Etapa 2, requisito 4).

Usa as mesmas variáveis de ambiente que o app.py já usava com psycopg2
(DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD), para não ter duas
configurações de banco diferentes no projeto.
"""
import os
import getpass

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


def _url():
    usuario = os.getenv("DB_USER", getpass.getuser())
    senha = os.getenv("DB_PASSWORD", "")
    host = os.getenv("DB_HOST", "localhost")
    porta = os.getenv("DB_PORT", "5432")
    banco = os.getenv("DB_NAME", "hospital_yuska")
    credencial = f"{usuario}:{senha}" if senha else usuario
    return f"postgresql+psycopg2://{credencial}@{host}:{porta}/{banco}"


engine = create_engine(_url(), future=True)

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)


class Base(DeclarativeBase):
    """Classe base declarativa de todos os models."""
