import tomllib
from platformdirs import user_config_path
from pydantic import ValidationError
from .exceptions import ConfigurationError
from .models import AppConfig

def load_config() -> AppConfig:
    config_path = user_config_path("bt_switch") / "config.toml"
    if not config_path.exists():
        raise ConfigurationError(f"Config not found at {config_path}")
    
    try:
        with config_path.open("rb") as f:
            return AppConfig.model_validate(tomllib.load(f))
    except (ValidationError, tomllib.TOMLDecodeError) as e:
        raise ConfigurationError(f"Config parse error: {e}")
