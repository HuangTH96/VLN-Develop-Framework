import os, yaml

def load_config(cfg_path: str):
    """Load configuration from YAML file"""
    try:
        if os.path.exists(cfg_path):
            with open(cfg_path, "r") as f:
                return yaml.safe_load(f) or {}
    except Exception as e:
        print(f"Warning: Could not load config from {cfg_path}: {e}")
    return {}