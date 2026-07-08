# AgentLens

Local cost & efficiency visibility for Claude Code sessions. Reads your existing
session logs under `~/.claude/projects/**/*.jsonl` — no extra instrumentation,
no API keys, no data leaves your machine.

## Usage

```bash
# Terminal summary of the last 7 days
python -m agentlens.cli scan --since 7d

# Full JSON output
python -m agentlens.cli scan --since 7d --json

# Self-contained HTML report (no JS, no external assets)
python -m agentlens.cli report --since 30d -o report.html
```

## What it detects

- **duplicate_read** — the same file read more than once in a session
- **low_cache_reuse** — `cache_creation_input_tokens` far exceeds
  `cache_read_input_tokens`, meaning context is being rebuilt more often than
  reused
- **batchable_tool_calls** — runs of consecutive single-tool-call turns fired
  in rapid succession that likely could have been batched into one turn

## Pricing

`pricing.yaml` holds USD-per-million-token rates per model plus the cache
write/read multipliers. Update it when Anthropic changes pricing — nothing in
the code needs to change. Time-limited introductory rates (e.g. a new model's
launch pricing) go in the `introductory_pricing` section with a `valid_until`
date; turns are priced against their own timestamp, so the standard rate in
`models` applies automatically once `valid_until` passes — no code change or
manual revert needed.

## Notes

- One Claude Code API response is logged as multiple JSONL lines (one per
  content block) sharing the same `message.id` and an identical usage object.
  `log_reader.parse_session` collapses these into one `Turn` — summing
  per-line would inflate token/cost totals several-fold.
- Cache writes are priced per their actual TTL: the session log's
  `cache_creation.ephemeral_5m_input_tokens` / `ephemeral_1h_input_tokens`
  are read separately and priced at the 1.25x / 2x multipliers respectively.
  Logs that predate this breakdown fall back to treating the full write as 5m.
