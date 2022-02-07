import logging
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker, session as sql_session
from sqlalchemy import event

from .exceptions import CorporaException
from backend.api.data_portal.config.app_config import DbConfig

logger = logging.getLogger(__name__)


class DBSessionMaker:

    _session_maker = None
    engine = None

    def __init__(self, database_uri: str = None):
        if not self.engine:
            self.database_uri = database_uri if database_uri else DbConfig().database_uri
            self.engine = create_engine(self.database_uri, connect_args={"connect_timeout": 5})

    def session(self, **kwargs) -> sql_session.Session:
        new_session = self.session_maker(info=dict(s3_deletion_list=[]), **kwargs)

        @event.listens_for(new_session, "after_commit")
        def cleanup_s3_objects(session):
            for func in session.info["s3_deletion_list"]:
                func()
            session.info["s3_deletion_list"].clear()

        return new_session

    @property
    def session_maker(self):
        if not self._session_maker:
            self._session_maker = sessionmaker(bind=self.engine)
        return self._session_maker


@contextmanager
def db_session_manager(**kwargs):
    """

    :param kwargs: passed to Session
    """
    try:
        session = DBSessionMaker().session(**kwargs)
        yield session
        if session.transaction:
            session.commit()
        else:
            session.expire_all()
    except SQLAlchemyError:
        session.rollback()
        msg = "Failed to commit."
        logger.exception(msg)
        raise CorporaException(msg)
    finally:
        session.close()
