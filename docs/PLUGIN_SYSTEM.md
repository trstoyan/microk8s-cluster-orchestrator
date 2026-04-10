# MKO Plugin System (v1)

The plugin system provides a business-agnostic extension model for checks and guarded actions.

## Security Model

- Only admin users can install, enable, disable, rollback, or execute plugin actions.
- Installations are restricted to allowlisted `repo_url` + pinned `commit` values.
- Actions use a two-step flow:
  1. Plan action and receive a signed short-lived confirmation token.
  2. Execute with explicit reason and confirmation token.

## Manifest

Plugins must include `.mko-plugin/plugin.json` with:

```json
{
  "id": "example_plugin",
  "name": "Example Plugin",
  "version": "0.1.0",
  "mko_plugin_api": "v1",
  "entrypoints": {
    "module": "plugin.py",
    "actions_factory": "get_actions",
    "health_factory": "collect_health"
  }
}
```

## Module Contract

- `collect_health() -> dict`
- `get_actions() -> list[dict]`

Supported action type in v1:
- `ansible_playbook`

Action fields:
- `id`, `name`, `description`
- `type = "ansible_playbook"`
- `playbook_path` (relative to plugin root)
- optional `targets`, `risk`

## API Endpoints

- `GET /api/plugins`
- `POST /api/plugins/install`
- `POST /api/plugins/{plugin_id}/enable`
- `POST /api/plugins/{plugin_id}/disable`
- `POST /api/plugins/{plugin_id}/rollback`
- `POST /api/plugins/{plugin_id}/apply`
- `GET /api/plugins/{plugin_id}/health`
- `POST /api/plugins/{plugin_id}/actions/plan`
- `POST /api/plugins/{plugin_id}/actions/execute`

## Cluster Apply

`/api/plugins/{plugin_id}/apply` packages the installed plugin as a ConfigMap and patches the configured MKO deployment annotation to trigger rollout.

Config keys:
- `plugins.k8s.namespace`
- `plugins.k8s.deployment`
