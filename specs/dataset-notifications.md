# Dataset Notifications

> **Prefix:** `DATASET_NOTIFICATIONS` — requirement IDs are `DATASET_NOTIFICATIONS-<NNN>`,
> sequential within this file. Never reuse or renumber an ID, even after a
> requirement is removed; mark removed requirements as such instead.

## Summary

The listener (`run.py`) turns HDX dataset and collection events from the Redis stream into Novu
notifications for subscribed users. This area defines which events notify whom, and how
dataset events are grouped into Novu workflow runs, which Novu bills per run. The design and
its rationale are in [docs/novu-event-aggregation-plan.md](../docs/novu-event-aggregation-plan.md).

## Scope

- Consuming HDX events from the Redis stream in the listener.
- Deciding whether an event is notification-worthy and who receives it.
- Buffering and aggregating dataset events before triggering Novu.
- The payload sent to Novu and the Novu email templates kept in `novu_templates/`.

### Out of scope

- Syncing subscriptions from CKAN (`sync.py`), a separate process.
- Producing events (`gisrestlayer`) and the Redis stream library (`hdx-redis-lib`).
- Throttling notifications per dataset (a cap on triggers per window).
- Aggregating collection events (`*-dataset-added`).
- The Novu workflow configuration itself (delay and digest steps), managed in the Novu dashboard.
- `novu_probe` in `hdx-notification-platform-stats`, a separate repo.

## Requirements

Status: `[x]` implemented, `[ ]` planned / not yet implemented.

### Event intake and filtering

- [x] **DATASET_NOTIFICATIONS-001** — The listener processes only events whose `event_type` is in `ALLOWED_EVENT_TYPES`: `resource-created`, `resource-deleted`, `resource-data-changed`, `spreadsheet-sheet-created`, `spreadsheet-sheet-deleted`, `spreadsheet-sheet-changed`, `organization-dataset-added`, `crisis-dataset-added`, `group-dataset-added`.
- [x] **DATASET_NOTIFICATIONS-002** — If `HDX_ENABLED_OBJECTS_CSV` is set, only events for objects listed in it notify. Otherwise, if `HDX_DISABLED_OBJECTS_CSV` is set, events for all objects except those listed notify. If neither list is loaded, no event notifies.
- [x] **DATASET_NOTIFICATIONS-003** — The enabled/disabled object lists are reloaded when they are older than `HDX_OBJECTS_CSV_EXPIRATION_HOURS` (default 1).
- [x] **DATASET_NOTIFICATIONS-004** — A dataset event whose `resource_name` contains any of `QuickCharts`, `qc_data.csv`, `quickcharts` or `Quickcharts` does not notify.
- [x] **DATASET_NOTIFICATIONS-005** — A `spreadsheet-sheet-changed` event whose changed fields are all in `NON_NOTIFYING_SPREADSHEET_FIELDS` (`nrows`) does not notify. If `changed_fields` is empty or missing, the event notifies (HDX-11617).
- [x] **DATASET_NOTIFICATIONS-006** — A dataset event notifies the users subscribed to that dataset, and a collection event the users subscribed to that organisation, group or crisis, as recorded in the `subscription` table. With no subscribers, nothing is sent.

### Novu triggers: legacy behaviour

- [x] **DATASET_NOTIFICATIONS-007** — A collection event triggers the `dataset-collection-notification` workflow once per subscriber.
- [x] **DATASET_NOTIFICATIONS-008** — While aggregation is disabled (see -010), every notifying dataset event triggers `dataset-notification-v2` once per subscriber. The payload contains `event`, `email_event_type`, `resource_name`, `change_summary`, `unsubscribe_token_key`, `hdx_url` and `dataset_id`.
- [x] **DATASET_NOTIFICATIONS-009** — `spreadsheet-sheet-*` events are sent with `email_event_type` `spreadsheet-sheet-updated`; other event types are sent with their own `event_type`.

### Aggregation of dataset events

- [ ] **DATASET_NOTIFICATIONS-010** — Aggregation is controlled by `DATASET_EVENT_AGGREGATION_ENABLED`, default `false`. With it off, dataset events behave exactly as in -008.
- [ ] **DATASET_NOTIFICATIONS-011** — With aggregation on, a dataset event that would notify under -002 to -006 is stored in the Postgres table `pending_dataset_event` (`id`, `dataset_id`, `event` as JSONB, `received_at` defaulting to the database's `now()`) instead of triggering Novu.
- [ ] **DATASET_NOTIFICATIONS-012** — A dataset's pending events become due when its newest `received_at` is at least `DATASET_EVENT_QUIET_PERIOD_SECONDS` (default 300) ago, or its oldest at least `DATASET_EVENT_MAX_WAIT_SECONDS` (default 1800) ago, measured with the database clock.
- [ ] **DATASET_NOTIFICATIONS-013** — Each listener instance attempts a flush at most once every `LISTENER_READ_BLOCK_MS` (default 30000), including when no stream events arrive.
- [ ] **DATASET_NOTIFICATIONS-014** — A flush claims all due datasets' events in one transaction: it takes the advisory lock `pg_try_advisory_xact_lock(FLUSH_LOCK_KEY)`, deletes the due rows with `DELETE … RETURNING`, and commits before any Novu call. If the lock is held by another instance, the flush skips that round without waiting.
- [ ] **DATASET_NOTIFICATIONS-015** — Each buffered event is part of at most one Novu trigger per subscriber. A crash after the claim's commit may lose that group for subscribers not yet triggered (at-most-once).
- [ ] **DATASET_NOTIFICATIONS-016** — For each claimed dataset, the flush looks up the current subscribers and triggers `NOVU_AGGREGATED_DATASET_WORKFLOW_ID` (default `dataset-notification-v3`) once per subscriber. A failure for one dataset is logged and does not stop the others.
- [ ] **DATASET_NOTIFICATIONS-017** — Within a claimed group, when a resource has a `resource-deleted` event, all of that resource's events with an earlier `event_time` are dropped. If those include its `resource-created`, the delete is dropped as well. Events are matched by `resource_id` and ordered by `event_time`; events without a `resource_id` are kept.
- [ ] **DATASET_NOTIFICATIONS-018** — After -017, the group's changes are de-duplicated on `(email_event_type, resource_id)`.
- [ ] **DATASET_NOTIFICATIONS-019** — A dataset whose changes are empty after -017 and -018 triggers nothing; its claimed rows are still removed.
- [ ] **DATASET_NOTIFICATIONS-020** — The aggregated payload contains:
  - `event`: `dataset_name`, `dataset_title`, `org_title`, `org_name`, `org_id`, `dataset_id` and `initiator_user_name` from the group's latest event, and `event_time` from its earliest event;
  - `changes[]`: `{email_event_type, resource_name, resource_id}` per change;
  - `hdx_url`, `unsubscribe_token_key` and `dataset_id`, in the same format as -008.
- [ ] **DATASET_NOTIFICATIONS-021** — Triggers carry no custom `transactionId`; Novu generates it, as today.
- [ ] **DATASET_NOTIFICATIONS-022** — Flushes run whether or not aggregation is enabled, so rows left after disabling it are still sent.
- [ ] **DATASET_NOTIFICATIONS-023** — Each flush logs the number of claimed events, the number of pending events, and the age of the oldest pending event.

### Listener runtime

- [ ] **DATASET_NOTIFICATIONS-024** — At startup the listener creates missing tables in one transaction holding `pg_advisory_xact_lock(INIT_LOCK_KEY)`, so instances starting together don't race.
- [ ] **DATASET_NOTIFICATIONS-025** — The listener reads the stream with its own loop using `read_hdx_event(block=LISTENER_READ_BLOCK_MS)` instead of `hdx_listen`. It keeps the current limit of 10,000 reads and the current behaviour of exiting the loop on an unhandled error.

### Email templates

- [ ] **DATASET_NOTIFICATIONS-026** — `novu_templates/dataset-notification-v3.html.liquid` renders the same email as v2. It reads file names and types from each digested event's `payload.changes[]` instead of `payload.resource_name` / `payload.email_event_type`.

### Novu requests

- [ ] **DATASET_NOTIFICATIONS-027** — Every Novu API request the listener makes, for both legacy (-007, -008) and aggregated (-016) triggers, uses `timeout=(10, 60)`: at most 10 s to connect and at most 60 s between bytes of the response. A timeout is logged and that trigger is dropped without retry, like any other failed Novu request.

## Notes / open questions

- **Novu request timeout (-027).**
  - Why: `requests` has no default timeout, so today a hung Novu call blocks that listener indefinitely.
  - Behaviour change: -027 also changes the legacy triggers in -007 and -008. A call that hangs now fails after the timeout and is logged, instead of blocking forever.
  - Worst case: if Novu stops responding, one subscriber can take up to ~70 s, so a 55-subscriber dataset can occupy a listener for about an hour, while the other instances carry on.
  - The values are code constants, not configuration.
- Delete handling (-017) applies within one claimed group only. If a file is updated in one group and deleted in a later group that falls in the same Novu 2h digest, the email lists both, as today.
- -015 is at-most-once by design, matching the stream: `hdx-redis-lib` acks each message before the listener processes it. The rationale is in the plan, under "Why the Novu calls happen after the commit".
- Possible typo in `novu_templates/dataset-notification-v2.html.liquid`: `split: '','` (extra `'`). Check it against the live Novu template; v3 (-026) uses the correct form.
- `FLUSH_LOCK_KEY` and `INIT_LOCK_KEY` are code constants, not configuration.
