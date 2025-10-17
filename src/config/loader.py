import yaml
from pathlib import Path

def load_feeds_config(file_path: str):
    """Carga el archivo YAML con los feeds."""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return data.get('feeds', [])
