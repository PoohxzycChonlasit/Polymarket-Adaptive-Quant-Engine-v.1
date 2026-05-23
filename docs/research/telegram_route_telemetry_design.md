# Telegram Route Telemetry Design

Date: 2026-05-23

Scope: docs-only design for minimal JSONL telemetry that makes Telegram notification routing observable without changing trading behavior.

Runtime behavior changed: No
Live behavior changed: No

## Goal

Add enough structured telemetry to answer:

- Was a Telegram alert route attempted?
- Was the notifier disabled or missing config?
- Was the alert suppressed by cooldown?
- Did the async send path report success or failure?
- Which runtime event triggered the notification route?

This design is observability-only. It must not alter strategy, risk, execution, order placement, paper/live mode, wallet behavior, or alert copy.

## Event Types

All Telegram route telemetry should be emitted as JSONL system-health or observability events. These events are diagnostic only.

Required event types:

- `telegram_route_attempt`
- `telegram_send_success`
- `telegram_send_failure`
- `telegram_suppressed_cooldown`
- `telegram_disabled`
- `telegram_missing_config`

## Common Fields

Every Telegram telemetry event should include:

| Field | Required | Description |
|---|---:|---|
| `timestamp` | Yes | UTC ISO-8601 timestamp when telemetry event was produced. |
| `event_type` | Yes | One of the Telegram event types listed above. |
| `route` | Yes | Logical alert route, such as `startup`, `entry`, `exit`, `risk`, `critical`, `incident`, `summary`, or `error_log`. |
| `run_id` | If available | Current runtime run id. Use `null` if unavailable. |
| `source_event_id` | If available | ID of triggering quant/runtime event. Use `null` if the source event has no id. |
| `cooldown_key` | If applicable | Dedup/cooldown key used by the alert layer. Use `null` when no cooldown applies. |
| `suppression_reason` | If applicable | Safe reason for suppression, such as `cooldown`, `disabled`, or `missing_config`. |
| `exception_class` | Failure only | Exception class name only, never exception message if it may include sensitive data. |

No event may include Telegram token, chat id, wallet secret, private key, full message body, raw HTTP response body, or user-visible alert text.

## Event Contracts

### telegram_route_attempt

Emit when code decides an alert should be routed to Telegram, before cooldown or send.

Required fields:

- `timestamp`
- `event_type`: `telegram_route_attempt`
- `route`
- `run_id`
- `source_event_id`
- `cooldown_key`

Example:

```json
{"timestamp":"2026-05-23T15:01:12.345Z","event_type":"telegram_route_attempt","route":"exit","run_id":"20260523_150000_12345","source_event_id":"trade_close:abc123","cooldown_key":null}
```

### telegram_send_success

Emit when the async send worker receives a successful Telegram API response.

Required fields:

- `timestamp`
- `event_type`: `telegram_send_success`
- `route`
- `run_id`
- `source_event_id`

Optional safe fields:

- `http_status`: numeric status code only
- `telegram_ok`: boolean if available

Do not store Telegram message id unless explicitly confirmed safe and useful later.

Example:

```json
{"timestamp":"2026-05-23T15:01:13.102Z","event_type":"telegram_send_success","route":"exit","run_id":"20260523_150000_12345","source_event_id":"trade_close:abc123","http_status":200,"telegram_ok":true}
```

### telegram_send_failure

Emit when send submission or async HTTP delivery fails.

Required fields:

- `timestamp`
- `event_type`: `telegram_send_failure`
- `route`
- `run_id`
- `source_event_id`
- `exception_class`

Optional safe fields:

- `http_status`: numeric status code if available
- `failure_stage`: `submit`, `http_post`, `response_status`, or `shutdown`

Do not include exception message by default. If a later implementation needs messages, it must sanitize tokens, URLs, chat ids, headers, and message text first.

Example:

```json
{"timestamp":"2026-05-23T15:01:13.102Z","event_type":"telegram_send_failure","route":"risk","run_id":"20260523_150000_12345","source_event_id":"risk_pause:def456","exception_class":"Timeout","failure_stage":"http_post"}
```

### telegram_suppressed_cooldown

Emit when an alert is intentionally not sent because a cooldown key is still active.

Required fields:

- `timestamp`
- `event_type`: `telegram_suppressed_cooldown`
- `route`
- `run_id`
- `source_event_id`
- `cooldown_key`
- `suppression_reason`: `cooldown`

Optional safe fields:

- `cooldown_seconds`
- `seconds_remaining`

Example:

```json
{"timestamp":"2026-05-23T15:02:01.000Z","event_type":"telegram_suppressed_cooldown","route":"incident","run_id":"20260523_150000_12345","source_event_id":"market_analysis_exception:ghi789","cooldown_key":"incident:BTC:market_analysis_exception","suppression_reason":"cooldown","cooldown_seconds":300,"seconds_remaining":241}
```

### telegram_disabled

Emit once per runtime startup when Telegram routing is disabled by configuration.

Required fields:

- `timestamp`
- `event_type`: `telegram_disabled`
- `route`: `startup`
- `run_id`
- `source_event_id`: `null`
- `suppression_reason`: `disabled`

Example:

```json
{"timestamp":"2026-05-23T15:00:00.100Z","event_type":"telegram_disabled","route":"startup","run_id":"20260523_150000_12345","source_event_id":null,"suppression_reason":"disabled"}
```

### telegram_missing_config

Emit once per runtime startup when Telegram appears enabled or partially configured but token/chat id is missing.

Required fields:

- `timestamp`
- `event_type`: `telegram_missing_config`
- `route`: `startup`
- `run_id`
- `source_event_id`: `null`
- `suppression_reason`: `missing_config`

Optional safe fields:

- `has_token`: boolean
- `has_chat_id`: boolean

Example:

```json
{"timestamp":"2026-05-23T15:00:00.120Z","event_type":"telegram_missing_config","route":"startup","run_id":"20260523_150000_12345","source_event_id":null,"suppression_reason":"missing_config","has_token":false,"has_chat_id":true}
```

## Route Names

Use stable route labels:

- `startup`
- `entry`
- `exit`
- `risk`
- `critical`
- `incident`
- `summary`
- `error_log`
- `daily_report`

Avoid embedding asset, market slug, position id, or message text inside `route`. Put linkage in `source_event_id` when safe.

## Source Event ID Rules

Preferred source ids:

- Entry: `trade_open:<event_id>` or `paper_fill:<event_id>` when available.
- Exit: `trade_close:<event_id>` when available.
- Risk: `risk_event:<event_id>` or stable risk reason if no event id exists.
- Incident: `incident:<event_id>` or specific structured incident id.
- Startup: `null`.
- Error log: `log:<record_created_ts>:<logger_name>` only if a stable event id is not available.

Fallback:

- Use `null` instead of fabricating unsafe or unstable ids.
- Do not use raw message body as a source id.
- Do not use secrets, wallet addresses, Telegram chat ids, or raw API URLs.

## Cooldown Rules

Cooldown telemetry should be emitted only for routes that are actually cooldown-limited:

- `risk`
- `critical`
- `incident`
- `summary`

Entry, exit, and startup routes should not emit `telegram_suppressed_cooldown` unless future code explicitly adds cooldown to those paths.

For suppressed alerts:

1. Emit `telegram_route_attempt`.
2. Emit `telegram_suppressed_cooldown`.
3. Do not emit `telegram_send_success` or `telegram_send_failure`.

## Disabled And Missing Config Rules

At startup:

- If Telegram is explicitly disabled, emit `telegram_disabled` once.
- If Telegram is enabled or partially configured but token/chat id is missing, emit `telegram_missing_config` once.
- Do not repeat these events every scan loop.

For later alert attempts when notifier is unavailable:

- Emit `telegram_route_attempt`.
- Emit `telegram_send_failure` with `exception_class` set to `NotifierUnavailable` and `failure_stage` set to `submit`.
- Do not raise.

## Fail-Soft Rules

Telegram telemetry must never:

- Block trading.
- Change order approval.
- Change risk state.
- Change strategy signals.
- Change execution behavior.
- Crash the runtime.
- Retry forever.
- Wait indefinitely for Telegram API responses.

Telemetry emission failures must be swallowed or logged at warning level at most. Trading logic remains authoritative.

## Security Rules

Never write these to JSONL:

- Telegram bot token.
- Telegram chat id.
- Private keys.
- Wallet secrets.
- Raw request headers.
- Raw Telegram API URL containing token.
- Full message body.
- Unredacted exception messages.
- Operator personal data.

Allowed:

- Boolean config presence flags such as `has_token` and `has_chat_id`.
- Safe exception class names such as `Timeout`, `HTTPError`, `ConnectionError`, or `NotifierUnavailable`.
- Numeric HTTP status code.
- Stable route label.
- Safe source event id.

## Health Summary Fields

A future session summary can aggregate these events into:

- `telegram_route_attempt_count`
- `telegram_send_success_count`
- `telegram_send_failure_count`
- `telegram_suppressed_cooldown_count`
- `telegram_disabled_count`
- `telegram_missing_config_count`
- `telegram_last_success_ts`
- `telegram_last_failure_ts`
- `telegram_last_failure_class`

These summary fields should remain observability-only.

## Implementation Boundary For Later Work

Allowed in a future implementation task:

- Add JSONL telemetry around Telegram alert routing.
- Add safe async callback result capture.
- Add targeted tests for route attempt, cooldown suppression, disabled config, missing config, send success, and send failure.

Not allowed without a separate explicit task:

- Strategy changes.
- Risk changes.
- Execution/order placement changes.
- Live-mode behavior changes.
- Alert copy redesign.
- Telegram spam expansion.
- Secrets in telemetry.
- Replay jobs.
- S3 promotion.

## Recommended Status

READY_FOR_OBSERVABILITY_ONLY_IMPLEMENTATION

Tests: not run; docs-only design.

