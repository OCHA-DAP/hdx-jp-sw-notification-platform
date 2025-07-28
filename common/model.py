
from sqlalchemy import Column, Index, UnicodeText, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from sqlalchemy.exc import IntegrityError
from common.db_utils import Base
from common.utils import generate_object_hash_id

# Base = declarative_base()


class NotifyObject(Base):
    __tablename__ = 'object'

    id = Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    type = Column('type', UnicodeText, nullable=False)
    hdx_id = Column('hdx_id', UnicodeText, nullable=False)

    # Relationships
    datasets = relationship('Dataset', back_populates='notify_object', cascade='all, delete-orphan')
    subscriptions = relationship('Subscription', back_populates='notify_object', cascade='all, delete-orphan')

    __table_args__ = (
        Index('ix_object_type_hdx_id', 'type', 'hdx_id'),
    )

    def __init__(self, type, hdx_id):
        self.type = type
        self.hdx_id = hdx_id

    @classmethod
    def get_or_create(cls, session, object_type, hdx_id):
        """Get existing object or create new one"""
        obj = session.query(cls).filter_by(type=object_type, hdx_id=hdx_id).first()
        if not obj:
            obj = cls(type=object_type, hdx_id=hdx_id)
            session.add(obj)
            session.flush()  # To get the ID
        return obj

    @classmethod
    def delete_objects_with_no_subscriptions(cls, session):
        """Delete objects that have no subscriptions"""
        orphaned_objects = session.query(cls).filter(
            ~cls.subscriptions.any()
        ).all()
        for obj in orphaned_objects:
            session.delete(obj)
        return len(orphaned_objects)


class Dataset(Base):
    __tablename__ = 'dataset'

    id = Column('id', UnicodeText, primary_key=True, nullable=False)  # This is the tid_hash
    dataset_id = Column('dataset_id', UnicodeText, nullable=False)
    notify_object_id = Column(
        'notify_object_id',
        UUID(as_uuid=True),
        ForeignKey('object.id', ondelete='CASCADE'),
        nullable=False
    )

    # Relationships
    notify_object = relationship('NotifyObject', back_populates='datasets')

    __table_args__ = (
        Index('ix_dataset_dataset_id', 'dataset_id'),
        Index('ix_dataset_notify_object_id', 'notify_object_id'),
    )

    def __init__(self, dataset_id, notify_object_id, object_type=None, object_hdx_id=None):
        self.dataset_id = dataset_id
        self.notify_object_id = notify_object_id
        # Generate the tid_hash as the id
        if object_type and object_hdx_id:
            self.id = generate_object_hash_id(object_type, object_hdx_id, dataset_id)
        else:
            # Will be set later when we have the object info
            self.id = None

    def set_id_from_object(self, object_type, object_hdx_id):
        """Set the dataset ID using object information"""
        self.id = generate_object_hash_id(object_type, object_hdx_id, self.dataset_id)

    @classmethod
    def bulk_insert_from_dicts(cls, session, data_dicts):
        try:
            session.execute(
                cls.__table__.insert(),
                data_dicts
            )
        except IntegrityError as e:
            session.rollback()
            raise e

    @classmethod
    def delete_by_ids(cls, session, id_list):
        if not id_list:
            return 0
        result = session.query(cls).filter(cls.id.in_(id_list)).delete(synchronize_session=False)
        return result

    @classmethod
    def get_by_notify_object_id(cls, session, notify_object_id):
        return session.query(cls).filter_by(notify_object_id=notify_object_id).all()


class Subscription(Base):
    __tablename__ = 'subscription'

    id = Column('id', UUID(as_uuid=True), primary_key=True, nullable=False)  # subscription_id from external system
    user_id = Column('user_id', UnicodeText, nullable=False)
    event_type = Column('event_type', UnicodeText, nullable=False)
    notify_object_id = Column(
        'notify_object_id',
        UUID(as_uuid=True),
        ForeignKey('object.id', ondelete='CASCADE'),
        nullable=False
    )

    # Relationships
    notify_object = relationship('NotifyObject', back_populates='subscriptions')

    __table_args__ = (
        UniqueConstraint('user_id', 'notify_object_id', name='uq_user_object'),
        Index('ix_subscription_user_id', 'user_id'),
        Index('ix_subscription_notify_object_id', 'notify_object_id'),
    )

    def __init__(self, subscription_id, user_id, event_type, notify_object_id):
        self.id = subscription_id
        self.user_id = user_id
        self.event_type = event_type
        self.notify_object_id = notify_object_id

    @classmethod
    def delete_by_ids(cls, session, subscription_ids):
        if not subscription_ids:
            return 0
        result = session.query(cls).filter(cls.id.in_(subscription_ids)).delete(synchronize_session=False)
        return result

    @classmethod
    def bulk_insert_from_dicts(cls, session, data_dicts):
        try:
            session.execute(
                cls.__table__.insert(),
                data_dicts
            )
        except IntegrityError as e:
            session.rollback()
            raise e

    @classmethod
    def get_by_notify_object_id(cls, session, notify_object_id):
        return session.query(cls).filter_by(notify_object_id=notify_object_id).all()

    @classmethod
    def get_users_subscribed_to_object(cls, session, object_type, object_id):
        """Get all user IDs subscribed to a specific object (dataset, organization, group, crisis)"""
        # Find the NotifyObject
        notify_object = session.query(NotifyObject).filter_by(
            type=object_type, hdx_id=object_id
        ).first()

        if not notify_object:
            return []

        # Get all subscriptions for this object
        subscriptions = session.query(cls).filter_by(
            notify_object_id=notify_object.id
        ).all()

        return [sub.user_id for sub in subscriptions]


# Keep DatasetToUser for backward compatibility during transition
# class DatasetToUser(Base):
#     __tablename__ = 'dataset_to_user'

#     id = Column('id', UnicodeText, primary_key=True, unique=True, nullable=False)
#     dataset_id = Column('dataset_id', UnicodeText, nullable=False)
#     object_id = Column('object_id', UnicodeText, nullable=False)
#     object_type = Column('object_type', UnicodeText, nullable=False)
#     user_id = Column('user_id', UnicodeText, nullable=False)
#     subscription_id = Column('subscription_id', UnicodeText, nullable=False)
#     event_type = Column('event_type', UnicodeText, nullable=False)
#     #object_type+object_id+dataset_id_hash
#     tid_hash = Column('tid_hash', UnicodeText, nullable=False)

#     __table_args__ = (
#         Index('ix_dataset_to_user_dataset_user', 'dataset_id', 'user_id'),
#     )

#     def __init__(self, user_id, object_id, object_type, subscription_id, dataset_id, event_type):
#         self.dataset_id = dataset_id
#         self.object_id = object_id
#         self.object_type = object_type
#         self.user_id = user_id
#         self.subscription_id = subscription_id
#         self.event_type = event_type
#         self.tid_hash = generate_object_hash_id(object_type, object_id, dataset_id)
#         self.id = generate_object_hash_id(object_type, object_id, dataset_id, subscription_id)

#     # def insert(self, session):
#     #     session.add(self)
#     #     session.commit()
#     #     session.refresh(self)
#     #     return self
#     #
#     # def update(self, session, **kwargs):
#     #     for key, value in kwargs.items():
#     #         if hasattr(self, key):
#     #             setattr(self, key, value)
#     #     session.commit()
#     #     session.refresh(self)
#     #     return self
#     #
#     # def delete(self, session):
#     #     session.delete(self)
#     #     session.commit()

#     # Bulk delete by ID list using ORM query
#     @classmethod
#     def bulk_delete_by_ids(cls, session, id_list):
#         session.query(cls).filter(cls.id.in_(id_list)).delete(synchronize_session=False)
#         #remove commit after insert also
#         session.commit()

#     @classmethod
#     def delete_by_subscription_ids(cls, session, subscription_ids):
#         if not subscription_ids:
#             return 0
#         result = session.query(cls).filter(cls.subscription_id.in_(subscription_ids)).delete(synchronize_session=False)
#         session.commit()
#         return result  # no deleted rows

#     @classmethod
#     def delete_by_tid_hash_list(cls, session, tid_hash_list):
#         if not tid_hash_list:
#             return 0
#         result = session.query(cls).filter(cls.tid_hash.in_(tid_hash_list)).delete(synchronize_session=False)
#         # session.commit()
#         return result  # no deleted rows

#     # Insert from dicts (if using plain data, not ORM objects)
#     @classmethod
#     def bulk_insert_from_dicts(cls, session, data_dicts):
#         try:
#             session.execute(
#                 cls.__table__.insert(),
#                 data_dicts
#             )
#             # session.commit()
#         except IntegrityError as e:
#             session.rollback()
#             raise e

#     @classmethod
#     def get_by_id(cls, session, record_id):
#         try:
#             return session.query(cls).filter_by(id=record_id).one()
#         except NoResultFound:
#             return None

#     @classmethod
#     def get_by_dataset_id(cls, session, dataset_id):
#         return session.query(cls).filter_by(dataset_id=dataset_id).all()

#     @classmethod
#     def get_by_object_id(cls, session, object_id):
#         return session.query(cls).filter_by(object_id=object_id).all()

#     @classmethod
#     def get_by_object_type(cls, session, object_type):
#         return session.query(cls).filter_by(object_type=object_type).all()

#     @classmethod
#     def get_by_user_id(cls, session, user_id):
#         return session.query(cls).filter_by(user_id=user_id).all()

#     @classmethod
#     def get_by_subscription_id(cls, session, subscription_id):
#         return session.query(cls).filter_by(subscription_id=subscription_id).all()

#     @classmethod
#     def get_by_tid_hash(cls, session, tid_hash):
#         return session.query(cls).filter_by(tid_hash=tid_hash).all()
