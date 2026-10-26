"""
Aggregation of dataset events: instead of one Novu trigger per resource event per subscriber, events are buffered
in Postgres and sent as one trigger per subscriber per dataset update run. See specs/dataset-notifications.md
(DATASET_NOTIFICATIONS-010 .. -023) and docs/novu-event-aggregation-plan.md.
"""
import collections
import logging
from typing import Dict, List

from common.model import PendingDatasetEvent, Subscription
from config.config import get_config
from listener_processing.helpers import build_changes, get_event_time, get_unsubscribe_token_key
from listener_processing.novu import AGGREGATED_DATASET_NOTIFICATION_WORKFLOW_ID, send_notifications_to_users

logger = logging.getLogger(__name__)

config = get_config()


def buffer_dataset_event(session, dataset_id: str, event: Dict):
    """Stores a notification-worthy dataset event until its dataset is due (DATASET_NOTIFICATIONS-011)."""
    PendingDatasetEvent.add(session, dataset_id, event)
    session.commit()


def build_aggregated_payload(dataset_id: str, events: List[Dict], changes: List[Dict]) -> Dict:
    """
    Payload for the aggregated workflow (DATASET_NOTIFICATIONS-020). `events` must be in chronological order.
    Only `dataset_name`, `dataset_title`, `org_title`, `event_time`, the `changes` names and types, `hdx_url` and
    `unsubscribe_token_key` are read by the email template; the ids and the other names are kept for debugging and
    for the stats tooling.
    """
    earliest, latest = events[0], events[-1]
    return {
        'event': {
            'dataset_name': latest.get('dataset_name'),
            'dataset_title': latest.get('dataset_title'),
            'org_title': latest.get('org_title'),
            'org_name': latest.get('org_name'),
            'org_id': latest.get('org_id'),
            'dataset_id': latest.get('dataset_id'),
            'initiator_user_name': latest.get('initiator_user_name'),
            'event_time': earliest.get('event_time'),
        },
        'changes': changes,
        'hdx_url': config.HDX_URL,
        'unsubscribe_token_key': get_unsubscribe_token_key(dataset_id),
        'dataset_id': dataset_id,
    }


def _send_dataset_group(session, dataset_id: str, events: List[Dict]):
    changes = build_changes(events)
    if not changes:
        logger.info(f'Nothing left to notify for dataset {dataset_id} after applying deletions '
                    f'({len(events)} events)')
        return

    user_ids = Subscription.get_users_subscribed_to_object(session, 'dataset', dataset_id)
    # end the read-only transaction before the Novu calls, so no transaction stays open while they run
    session.commit()
    if not user_ids:
        logger.info(f'No users subscribed to dataset {dataset_id}')
        return

    payload = build_aggregated_payload(dataset_id, events, changes)
    send_notifications_to_users(user_ids, payload, is_collection_event=False,
                                dataset_workflow_id=AGGREGATED_DATASET_NOTIFICATION_WORKFLOW_ID)
    logger.info(f'Sent aggregated dataset notifications to {len(user_ids)} users for dataset {dataset_id}: '
                f'{len(changes)} changes from {len(events)} events')


def flush_due_dataset_events(session):
    """
    Claims the pending events of every due dataset and sends one notification per subscriber per dataset
    (DATASET_NOTIFICATIONS-014 .. -016, -019, -023). The claim is committed before any Novu call, so a crash while
    sending loses that group for the subscribers not yet notified, but never sends it twice.
    """
    try:
        try:
            rows = PendingDatasetEvent.claim_due(
                session, config.DATASET_EVENT_QUIET_PERIOD_SECONDS, config.DATASET_EVENT_MAX_WAIT_SECONDS
            )
            session.commit()
        except Exception:
            session.rollback()
            raise

        if rows is None:
            logger.debug('Another listener instance is flushing pending dataset events; skipping this round')
            return

        events_by_dataset = collections.defaultdict(list)
        for row in sorted(rows, key=lambda r: (get_event_time(r.event), r.id)):
            events_by_dataset[row.dataset_id].append(row.event)

        for dataset_id, events in events_by_dataset.items():
            try:
                _send_dataset_group(session, dataset_id, events)
            except Exception as e:
                session.rollback()
                logger.error(f'Error sending aggregated notifications for dataset {dataset_id}: {e}')

        pending_count, oldest_age = PendingDatasetEvent.get_pending_stats(session)
        session.commit()
        logger.info(f'Flushed {len(rows)} pending dataset events for {len(events_by_dataset)} datasets; '
                    f'{pending_count} still pending, oldest {oldest_age}')
    finally:
        session.close()
