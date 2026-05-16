# Daily Research Notes

Use this folder for one research note per day.

Daily notes are meant to reduce context loss between Codex, Claude, Gemini, ChatGPT, and human operator sessions. They should summarize what happened without becoming a secret store or raw log dump.

## File Naming

Use one file per day:

```text
YYYY-MM-DD.md
```

## What To Include

- AI actions performed.
- Branch and commit references.
- Files modified.
- Tests or checks run.
- Runtime commands used.
- Offline reports generated.
- Selected run_id values.
- Continuity verdicts.
- Replay evidence.
- Trade count, fills, exits, and PnL when relevant.
- Primary and secondary bottlenecks.
- Unresolved issues.
- Safe next prompts.

## What Not To Include

- Private keys.
- Wallet credentials.
- API keys.
- Telegram bot tokens.
- Chat IDs.
- Raw secrets from `.env`.
- Full raw JSONL dumps.
- Anything that would enable unintended live trading.

## Workflow

1. Start from `research/session_memory_template.md`.
2. Keep the note compact.
3. Prefer counts, paths, and verdicts over raw logs.
4. Link generated reports by path instead of pasting full contents.
5. End with a safe next Codex prompt and a safe next ChatGPT prompt.

## Safety Boundary

Daily notes are memory aids only. They do not authorize runtime changes, strategy changes, risk changes, live trading, hooks, MCP execution, or automatic command execution.
