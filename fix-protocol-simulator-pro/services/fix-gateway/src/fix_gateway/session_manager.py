# fix-protocol-simulator-pro/services/fix-gateway/src/fix_gateway/session_manager.py

import uuid
from datetime import datetime

# now
from fix_gateway.utils.logger import get_logger

# later
# from common_utils.logger import configure_logging, get_logger

from shared.observability.metrics import fix_sessions_active

logger = get_logger(__name__)


class Session:
    def __init__(self, sender_comp_id: str):
        self.session_id = str(uuid.uuid4())
        self.sender_comp_id = sender_comp_id
        self.created_at = datetime.utcnow()
        self.last_heartbeat = datetime.utcnow()
        logger.info(f"session created {self.session_id}")


class SessionManager:
    def __init__(self):
        self.sessions = {}

    def create_session(self, sender_comp_id: str) -> Session:
        if sender_comp_id not in self.sessions:
            fix_sessions_active.inc()
        session = Session(sender_comp_id)
        self.sessions[sender_comp_id] = session
        return session

    def get_session(self, sender_comp_id: str):
        return self.sessions.get(sender_comp_id)

    def update_heartbeat(self, sender_comp_id: str):
        session = self.get_session(sender_comp_id)
        if session:
            session.last_heartbeat = datetime.utcnow()
            logger.debug(f"heartbeat updated {session.session_id}")
