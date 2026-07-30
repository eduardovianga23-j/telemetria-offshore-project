from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Nome do ficheiro da base de dados local
SQLALCHEMY_DATABASE_URL = "sqlite:///./telemetria.db"
# Para PostgreSQL no futuro, seria: "postgresql://user:password@localhost/telemetria_db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Helper para gerir a sessão da BD em cada pedido da API
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()