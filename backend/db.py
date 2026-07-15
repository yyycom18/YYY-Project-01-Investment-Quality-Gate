from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from pathlib import Path
ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT.parent / "data" / "nalanda.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
ENGINE = create_engine(f"sqlite:///{DB_PATH}", future=True)

def init_db(schema_path: str = None):
    if schema_path is None:
        schema_path = str(Path(__file__).resolve().parent / "schema.sql")
    try:
        with ENGINE.begin() as conn:
            sql = Path(schema_path).read_text(encoding="utf-8")
            conn.execute(text(sql))
    except SQLAlchemyError as e:
        print("DB init error:", e)

def get_engine():
    return ENGINE

