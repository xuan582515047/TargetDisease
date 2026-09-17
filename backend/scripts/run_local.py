"""Local development entry point with a persistent SQLite database."""
import base64
import os
from pathlib import Path
import secrets

ROOT = Path(__file__).resolve().parents[2]
local_env = ROOT / '.env.local'
if not local_env.exists():
    local_env.write_text(
        'SECRET_KEY=' + secrets.token_urlsafe(48) + '\n'
        'CREDENTIAL_MASTER_KEY=' + base64.urlsafe_b64encode(os.urandom(32)).decode() + '\n',
        encoding='utf-8',
    )
from dotenv import load_dotenv
load_dotenv(local_env)
os.environ.setdefault('DATABASE_URL', 'sqlite:///' + (ROOT / 'backend' / 'local.db').as_posix())

from app.db.base import Base
from app.db import models  # noqa: F401
from app.db.session import engine
import uvicorn

if __name__ == '__main__':
    Base.metadata.create_all(engine)
    uvicorn.run('app.main:app', host='127.0.0.1', port=8000)
