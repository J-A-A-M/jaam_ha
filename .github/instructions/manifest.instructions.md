---
applyTo: "**/manifest.json"
---

# Manifest Instructions

**Applies to:** `custom_components/jaam_ha/manifest.json`

## Schema Validation

**Schema:** `/schemas/json/manifest_schema.json`

This schema combines Home Assistant's official manifest requirements with HACS-specific fields. Always validate against this schema.

## Required Fields

```json
{
  "domain": "jaam_ha",
  "name": "JAAM Home Assistant Integration",
  "codeowners": ["@J-A-A-M"],
  "config_flow": true,
  "documentation": "https://github.com/J-A-A-M/jaam_ha",
  "integration_type": "device",
  "iot_class": "cloud_polling",
  "issue_tracker": "https://github.com/J-A-A-M/jaam_ha/issues",
  "requirements": [],
  "version": "0.0.0"
}
```

## Field Reference

**Core fields:**

- `domain` - Integration identifier (matches directory name)
- `name` - Display name in Home Assistant
- `version` - Semantic version (required for HACS)
- `documentation` - Link to documentation
- `issue_tracker` - Link to GitHub issues (required for HACS)
- `codeowners` - GitHub usernames for notifications

**Integration behavior:**

- `config_flow` - Boolean, true if integration has UI config
- `integration_type` - One of: `device`, `hub`, `service`, `helper`, `system`, `virtual`
- `iot_class` - Connectivity type (see below)
- `requirements` - Python package dependencies

**Optional fields:**

- `dependencies` - Home Assistant integrations this depends on
- `after_dependencies` - Load after these integrations
- `dhcp`, `zeroconf`, `ssdp`, `usb`, `bluetooth` - Discovery configs
- `homekit`, `mqtt` - Protocol configs

## IoT Class Values

Choose the most accurate:

- `cloud_polling` - Cloud API with polling
- `cloud_push` - Cloud API with push updates
- `local_polling` - Local device with polling
- `local_push` - Local device with push updates
- `calculated` - Derived from other entities
- `assumed_state` - Cannot verify state

## Requirements Format

Use package name with version constraint:

```json
"requirements": [
  "aiohttp>=3.9.0",
  "some-package==1.2.3"
]
```

## Codeowners Format

GitHub usernames with `@` prefix:

```json
"codeowners": [
  "@J-A-A-M"
]
```

## Version

Use semantic versioning: `MAJOR.MINOR.PATCH`

- Increment MAJOR for breaking changes
- Increment MINOR for new features
- Increment PATCH for bug fixes

## Validation

Manifest is validated by:

- Home Assistant on integration load
- HACS validation
- Schema validator

Errors appear in Home Assistant logs.

## Common Mistakes

- ❌ Missing `version` (required for HACS)
- ❌ Missing `issue_tracker` (required for HACS)
- ❌ Wrong `domain` (must match directory)
- ❌ Invalid `iot_class` value
- ❌ Unquoted version numbers
- ❌ Trailing commas in JSON

## References

- [Manifest Documentation](https://developers.home-assistant.io/docs/creating_integration_manifest/)
- [IoT Class](https://developers.home-assistant.io/docs/integration_quality_scale_index#iot-class)
- [HACS Requirements](https://hacs.xyz/docs/publish/include)
