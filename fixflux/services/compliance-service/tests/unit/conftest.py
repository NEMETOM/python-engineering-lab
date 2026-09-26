import os
from unittest.mock import MagicMock

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://test:test@localhost/testdb")

import compliance_service.infrastructure.db as _db

_db.Base.metadata.create_all = MagicMock()
