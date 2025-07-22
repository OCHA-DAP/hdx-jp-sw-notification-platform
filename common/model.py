
from sqlalchemy import Column, Index, UnicodeText

from sqlalchemy.exc import NoResultFound
from sqlalchemy.exc import IntegrityError
from common.db_utils import Base
from common.utils import generate_object_hash_id

# Base = declarative_base()


class DatasetToUser(Base):
    __tablename__ = 'dataset_to_user'

    id = Column('id', UnicodeText, primary_key=True, unique=True, nullable=False)
    dataset_id = Column('dataset_id', UnicodeText, nullable=False)
    object_id = Column('object_id', UnicodeText, nullable=False)
    object_type = Column('object_type', UnicodeText, nullable=False)
    user_id = Column('user_id', UnicodeText, nullable=False)
    subscription_id = Column('subscription_id', UnicodeText, nullable=False)
    event_type = Column('event_type', UnicodeText, nullable=False)
    #object_type+object_id+dataset_id_hash
    tid_hash = Column('tid_hash', UnicodeText, nullable=False)

    __table_args__ = (
        Index('ix_dataset_to_user_dataset_user', 'dataset_id', 'user_id'),
    )

    def __init__(self, user_id, object_id, object_type, subscription_id, dataset_id, event_type):
        self.dataset_id = dataset_id
        self.object_id = object_id
        self.object_type = object_type
        self.user_id = user_id
        self.subscription_id = subscription_id
        self.event_type = event_type
        self.tid_hash = generate_object_hash_id(object_type, object_id, dataset_id)
        self.id = generate_object_hash_id(object_type, object_id, dataset_id, subscription_id)

    # def insert(self, session):
    #     session.add(self)
    #     session.commit()
    #     session.refresh(self)
    #     return self
    #
    # def update(self, session, **kwargs):
    #     for key, value in kwargs.items():
    #         if hasattr(self, key):
    #             setattr(self, key, value)
    #     session.commit()
    #     session.refresh(self)
    #     return self
    #
    # def delete(self, session):
    #     session.delete(self)
    #     session.commit()

    # Bulk delete by ID list using ORM query
    @classmethod
    def bulk_delete_by_ids(cls, session, id_list):
        session.query(cls).filter(cls.id.in_(id_list)).delete(synchronize_session=False)
        #remove commit after insert also
        session.commit()

    @classmethod
    def delete_by_subscription_ids(cls, session, subscription_ids):
        if not subscription_ids:
            return 0
        result = session.query(cls).filter(cls.subscription_id.in_(subscription_ids)).delete(synchronize_session=False)
        session.commit()
        return result  # no deleted rows

    @classmethod
    def delete_by_tid_hash_list(cls, session, tid_hash_list):
        if not tid_hash_list:
            return 0
        result = session.query(cls).filter(cls.tid_hash.in_(tid_hash_list)).delete(synchronize_session=False)
        # session.commit()
        return result  # no deleted rows

    # Insert from dicts (if using plain data, not ORM objects)
    @classmethod
    def bulk_insert_from_dicts(cls, session, data_dicts):
        try:
            session.execute(
                cls.__table__.insert(),
                data_dicts
            )
            # session.commit()
        except IntegrityError as e:
            session.rollback()
            raise e

    @classmethod
    def get_by_id(cls, session, record_id):
        try:
            return session.query(cls).filter_by(id=record_id).one()
        except NoResultFound:
            return None

    @classmethod
    def get_by_dataset_id(cls, session, dataset_id):
        return session.query(cls).filter_by(dataset_id=dataset_id).all()

    @classmethod
    def get_by_object_id(cls, session, object_id):
        return session.query(cls).filter_by(object_id=object_id).all()

    @classmethod
    def get_by_object_type(cls, session, object_type):
        return session.query(cls).filter_by(object_type=object_type).all()

    @classmethod
    def get_by_user_id(cls, session, user_id):
        return session.query(cls).filter_by(user_id=user_id).all()

    @classmethod
    def get_by_subscription_id(cls, session, subscription_id):
        return session.query(cls).filter_by(subscription_id=subscription_id).all()

    @classmethod
    def get_by_tid_hash(cls, session, tid_hash):
        return session.query(cls).filter_by(tid_hash=tid_hash).all()
