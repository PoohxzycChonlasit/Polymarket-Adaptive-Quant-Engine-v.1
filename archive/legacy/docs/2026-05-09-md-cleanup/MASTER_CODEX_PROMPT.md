# MASTER_CODEX_PROMPT.md

Before doing any work:

1. Read ONLY:

- README_QUICK_CONTEXT.md
- PROJECT_RULES.md
- ARCHITECTURE.md
- TASK_REQUEST.md

2. Do NOT scan the entire repository.
3. After reading docs:

- summarize current architecture
- summarize current runtime constraints
- summarize current task
- list ONLY the files relevant to the task
- list intentionally ignored files/directories

4. Token discipline:

- avoid recursive repository scans
- avoid unrelated tests/modules
- avoid runtime/log/archive/generated files
- inspect only targeted modules

5. Preserve architecture:

- websocket-first
- REST fallback only
- paper-safe by default
- risk-first
- lightweight logging
- VPS-friendly runtime

6. Preserve safety:

- do not loosen risk controls
- do not bypass order validation
- do not remove stale data protections
- do not merge paper/live logic

7. Make minimal diffs only.
8. Add only focused tests for modified behavior.
9. Before editing:

- explain why each inspected file is necessary
- explain which files are intentionally untouched

10. After editing:

- summarize modified files
- summarize behavior changes
- summarize tests added
- summarize token-saving decisions taken
