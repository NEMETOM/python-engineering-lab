import os
from unittest.mock import MagicMock

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/testdb")

import compliance_service.infrastructure.db as _db  # noqa: E402

_db.Base.metadata.create_all = MagicMock()
