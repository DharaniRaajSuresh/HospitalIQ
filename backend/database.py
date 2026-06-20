"""
WHAT THIS FILE DOES:
Manages the database connection. Tries PostgreSQL first, falls back to SQLite
if unavailable. Creates the database engine and provides a get_db() function
that FastAPI uses to give each request its own database session.

The database contains all the hospital data — beds, mortality records,
hospital information, patient admissions — stored in tables defined in models/.
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from backend.config import settings
from backend.models import Base
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

db_url = settings.database_url

def is_postgres_available(url: str) -> bool:
    if "sqlite" in url:
        return False
    try:
        engine_sync = create_engine(url, connect_args={"connect_timeout": 2})
        with engine_sync.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.warning("PostgreSQL check failed: %s", e)
        return False

# Automatic fallback to local SQLite database if Postgres is unreachable
if "postgresql" in db_url and not is_postgres_available(db_url):
    db_dir = Path(__file__).parent.parent / "ml_pipeline" / "data"
    db_dir.mkdir(parents=True, exist_ok=True)
    db_url = f"sqlite:///{db_dir}/hospitaliq.db"
    logger.warning(f"⚠️ PostgreSQL not reachable. Falling back to local SQLite at {db_url}")

# Create engine
if "sqlite" in db_url:
    engine = create_engine(
        db_url,
        echo=settings.debug,
        connect_args={
            "check_same_thread": False,
            "timeout": 30,
        },
    )
    # Enable WAL mode and larger cache for much better concurrent read performance
    from sqlalchemy import event
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")       # allows parallel reads
        cursor.execute("PRAGMA synchronous=NORMAL")      # faster writes, safe
        cursor.execute("PRAGMA cache_size=-65536")       # 64 MB page cache
        cursor.execute("PRAGMA temp_store=MEMORY")       # temp tables in RAM
        cursor.execute("PRAGMA mmap_size=268435456")     # 256 MB memory-mapped I/O
        cursor.close()
else:
    engine = create_engine(
        db_url,
        echo=settings.debug,
        pool_pre_ping=True,
    )

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def _run_migrations():
    """Add Google OAuth columns to users table if missing (supports both SQLite and PostgreSQL)."""
    try:
        with engine.connect() as conn:
            if "sqlite" in db_url:
                result = conn.execute(text("PRAGMA table_info(users)")).fetchall()
                existing = {row[1] for row in result}
            else:
                result = conn.execute(text(
                    "SELECT column_name FROM information_schema.columns WHERE table_name='users'"
                )).fetchall()
                existing = {row[0] for row in result}

        if "sqlite" in db_url:
            # Check if hashed_password is NOT NULL — if so, recreate table to make it nullable
            pw_notnull = any(row[1] == "hashed_password" and row[3] == 1 for row in result)
            if pw_notnull:
                logger.warning("⚠️ hashed_password is NOT NULL — recreating users table to allow Google-only users")
                with engine.connect() as conn:
                    conn.execute(text("""
                        CREATE TABLE users_new (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            email VARCHAR(255) NOT NULL UNIQUE,
                            hashed_password VARCHAR(255),
                            google_id VARCHAR(255) UNIQUE,
                            avatar_url VARCHAR(500),
                            full_name VARCHAR(255),
                            role VARCHAR(50) DEFAULT 'viewer',
                            is_active BOOLEAN DEFAULT 1,
                            created_at DATETIME
                        )
                    """))
                    conn.execute(text("""
                        INSERT INTO users_new (id, email, hashed_password, full_name, role, is_active, created_at)
                        SELECT id, email, hashed_password, full_name, role, is_active, created_at FROM users
                    """))
                    conn.execute(text("DROP TABLE users"))
                    conn.execute(text("ALTER TABLE users_new RENAME TO users"))
                    conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users(email)"))
                    conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_google_id ON users(google_id)"))
                    conn.commit()
                    logger.info("✅ users table recreated with nullable hashed_password")
                # Re-read columns after recreation
                result = conn.execute(text("PRAGMA table_info(users)")).fetchall()
                existing = {row[1] for row in result}

        for col, col_type in [("google_id", "VARCHAR(255)"), ("avatar_url", "VARCHAR(500)")]:
            if col not in existing:
                with engine.connect() as conn:
                    conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {col_type}"))
                    conn.commit()
                    logger.info("✅ Added column '%s' to users table", col)
        # Add unique index for google_id if it doesn't exist (can't ALTER ADD CONSTRAINT in SQLite)
        if "google_id" not in existing:
            with engine.connect() as conn:
                try:
                    conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_google_id ON users(google_id)"))
                    conn.commit()
                except Exception:
                    pass  # index may already exist
    except Exception as e:
        logger.warning("Migration note: %s (table may not exist yet, will be created below)", e)


def init_db():
    """Initialize database tables"""
    logger.info("🔄 Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    _run_migrations()
    logger.info("✅ Database tables created/verified")


def get_db() -> Session:
    """Get database session for dependency injection"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    """Check if database is connected"""
    try:
        with engine.connect() as connection:
            logger.info("✅ Database connection successful")
            return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False
