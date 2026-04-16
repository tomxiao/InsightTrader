import copy
from typing import Any, Dict, Optional

import tradingagents.default_config as default_config

# Use default config but allow it to be overridden
_config: Optional[Dict] = None
_runtime_context: Dict[str, Any] = {}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def initialize_config():
    """Initialize the configuration with default values."""
    global _config
    if _config is None:
        _config = copy.deepcopy(default_config.DEFAULT_CONFIG)


def set_config(config: Dict):
    """Update the configuration with custom values."""
    global _config
    if _config is None:
        _config = copy.deepcopy(default_config.DEFAULT_CONFIG)
    _config = _deep_merge(_config, config)


def get_config() -> Dict:
    """Get the current configuration."""
    if _config is None:
        initialize_config()
    return copy.deepcopy(_config or {})


def set_runtime_context(**kwargs):
    """Set runtime-only context used by data routing."""
    global _runtime_context
    _runtime_context.update(kwargs)


def clear_runtime_context():
    """Clear runtime-only context used by data routing."""
    global _runtime_context
    _runtime_context = {}


def get_runtime_context() -> Dict[str, Any]:
    """Get runtime-only routing context."""
    return copy.deepcopy(_runtime_context)


# Initialize with default config
initialize_config()
