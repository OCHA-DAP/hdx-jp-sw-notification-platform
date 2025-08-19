from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from config.config import get_config

config = get_config()

DATABASE_URL = f'postgresql://{config.HDX_NOTIFICATIONSDB_USER}:{config.HDX_NOTIFICATIONSDB_PASS}@{config.HDX_NOTIFICATIONSDB_ADDR}:{config.HDX_NOTIFICATIONSDB_PORT}/{config.HDX_NOTIFICATIONSDB_DB}'
Base = declarative_base()

SESSION = None
_engine = None

def session_creator() -> sessionmaker[Session]:
    global _engine
    _engine = create_engine(DATABASE_URL)
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return session_local

def db_session() -> Session:
    global SESSION
    if SESSION is None:
        session_local = session_creator()
        SESSION = session_local()
    return SESSION

def end_session():
    global SESSION
    if SESSION:
        SESSION.rollback()
        SESSION.flush()
        SESSION.close()
    SESSION = None

def commit_db_changes():
    db_session().commit()

def end_db_session():
    end_session()

def init_db():
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(bind=_engine)
    print('DB initialized')

def test_db():
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL)
    try:
        with _engine.connect() as connection:
            result = connection.execute(text('SELECT version();'))
            print('Connected to PostgreSQL:')
            for row in result:
                print(row[0])
    except Exception as e:
        print(f'Connection failed: {e}')
