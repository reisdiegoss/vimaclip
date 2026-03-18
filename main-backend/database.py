# =============================================
# VimaClip - Backend Principal
# Configuração do Banco de Dados (SQLite + SQLModel)
# =============================================

import os
from dotenv import load_dotenv
from sqlmodel import SQLModel, create_engine, Session

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./db/vimaclip.db")

# O check_same_thread=False é necessário para SQLite com FastAPI
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False}
)

def create_db_and_tables():
    """Cria o banco de dados e as tabelas definidas nos modelos."""
    SQLModel.metadata.create_all(engine)

def get_session():
    """Dependency injection para sessões do banco de dados."""
    with Session(engine) as session:
        yield session
