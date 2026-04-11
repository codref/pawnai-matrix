import logging
from pawnai_matrix.models import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

log = logging.getLogger(__name__)


class Storage:
    def __init__(self, database_connection_string):
        self.engine = create_engine(database_connection_string, echo=False)
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(self.engine)

        log.info(f"Database is connected and initialized")

    def get_session(self):
        return self.session()
