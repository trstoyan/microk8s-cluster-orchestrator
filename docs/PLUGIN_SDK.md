# MKO Plugin SDK (v1)

This SDK contract is business-agnostic and intended for downstream plugin repositories.

## Quick Start

Generate a scaffold:

```bash
python scripts/plugins/create_plugin_scaffold.py \
  --output-dir /tmp/my-plugin \
  --plugin-id system_health \
  --plugin-name "System Health Plugin"
```

## Required Structure

- `.mko-plugin/plugin.json`
- `plugin.py`
- action playbooks referenced by `playbook_path`

## Manifest Contract

Required fields:

- `id`
- `name`
- `version`
- `mko_plugin_api` (must be `v1`)
- `entrypoints.module`

Optional entrypoint overrides:

- `entrypoints.actions_factory` (default: `get_actions`)
- `entrypoints.health_factory` (default: `collect_health`)

## Action Contract

Current runtime supports `ansible_playbook` actions:

- `id` (string)
- `name` (string)
- `description` (string)
- `type` (must be `ansible_playbook`)
- `playbook_path` (relative path within plugin root)
- optional `targets` list (defaults to `[{\"type\": \"all_nodes\"}]`)

## Safety Rules

- Plugin source must come from allowlisted repository + pinned commit.
- Paths that escape plugin root are rejected.
- Mutating execution uses two-step plan+execute confirmation.
- Optional idempotency key is supported for execute requests.
