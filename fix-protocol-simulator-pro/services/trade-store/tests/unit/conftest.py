from unittest.mock import MagicMock

import shared.infrastructure.db as _db

# Prevent Base.metadata.create_all from connecting to the DB
# when trade_store.api.main is imported during test collection.
_db.Base.metadata.create_all = MagicMock()
