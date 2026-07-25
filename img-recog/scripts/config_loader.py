"""Load and resolve provider/model configuration from ~/.wmyskills/img_recog/."""

import os
import sys
import yaml

CONFIG_DIR = os.path.expanduser("~/.wmyskills/img_recog")
PROVIDER_FILE = os.path.join(CONFIG_DIR, "provider.yaml")
MODEL_FILE = os.path.join(CONFIG_DIR, "model.yaml")


def _load_yaml(path: str, label: str) -> dict:
    if not os.path.exists(path):
        print(f"Error: {label} not found at {path}", file=sys.stderr)
        print(f"Create it with provider entries. See SKILL.md for instructions.", file=sys.stderr)
        sys.exit(1)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if data is None:
            print(f"Error: {label} is empty or contains only comments", file=sys.stderr)
            sys.exit(1)
        if not isinstance(data, dict):
            print(f"Error: {label} must be a YAML mapping, got {type(data).__name__}", file=sys.stderr)
            sys.exit(1)
        return data
    except yaml.YAMLError as e:
        print(f"Error: Invalid YAML in {label}: {e}", file=sys.stderr)
        sys.exit(1)


def load_provider_config() -> dict:
    """Load provider.yaml and return {provider_name: {base_url, api_key}}."""
    data = _load_yaml(PROVIDER_FILE, "provider config")
    providers = data.get("providers", {})
    if not providers:
        print("Error: No providers defined in provider.yaml", file=sys.stderr)
        sys.exit(1)
    for name, cfg in providers.items():
        if not cfg.get("base_url") or not cfg.get("api_key"):
            print(f"Error: Provider '{name}' missing base_url or api_key", file=sys.stderr)
            sys.exit(1)
    return providers


def load_model_config() -> dict:
    """Load model.yaml and return full parsed dict."""
    data = _load_yaml(MODEL_FILE, "model config")
    if "default" not in data:
        print("Error: model.yaml missing 'default' section", file=sys.stderr)
        sys.exit(1)
    return data


def resolve_model(provider_name: str | None, model_name: str | None,
                  model_config: dict) -> tuple[str, str]:
    """Resolve provider and model name from CLI args + config defaults.

    Returns (provider_name, model_name).
    Raises SystemExit on resolution failure.
    """
    providers_cfg = model_config.get("providers", {})
    default = model_config.get("default", {})

    # Resolve provider
    if provider_name is None:
        provider_name = default.get("provider")
        if not provider_name:
            print("Error: No --provider given and no default provider in model.yaml", file=sys.stderr)
            sys.exit(1)

    if provider_name not in providers_cfg:
        available = list(providers_cfg.keys())
        print(f"Error: Provider '{provider_name}' not found in model.yaml", file=sys.stderr)
        print(f"Available providers: {', '.join(available)}", file=sys.stderr)
        sys.exit(1)

    models = providers_cfg[provider_name].get("models", [])
    if not models:
        print(f"Error: Provider '{provider_name}' has no vision models configured", file=sys.stderr)
        sys.exit(1)

    # Resolve model
    if model_name is None:
        if provider_name == default.get("provider") and default.get("model"):
            model_name = default["model"]
        else:
            print(f"Error: --model required for provider '{provider_name}'", file=sys.stderr)
            print(f"Available models: {', '.join(models)}", file=sys.stderr)
            sys.exit(1)

    if model_name not in models:
        print(f"Error: Model '{model_name}' not found for provider '{provider_name}'", file=sys.stderr)
        print(f"Available models: {', '.join(models)}", file=sys.stderr)
        sys.exit(1)

    return provider_name, model_name
