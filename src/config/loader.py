import yaml
from pathlib import Path
from typing import List, Dict, Any

def load_feeds_config(file_path: str):
    """Carga el archivo YAML con los feeds."""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return data.get('feeds', [])

def load_exclusions_config(file_path: str) -> Dict[str, Any]:
    """
    Carga la configuración de exclusiones desde el archivo YAML.

    Args:
        file_path: Ruta al archivo de configuración YAML

    Returns:
        Diccionario con la configuración de exclusiones
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return data.get('exclusions', {})

def get_chunks_all_exclusions(file_path: str, source_type: str) -> List[str]:
    """
    Obtiene las categorías a excluir de los archivos -all para un sourceType específico.

    Args:
        file_path: Ruta al archivo de configuración YAML
        source_type: Tipo de fuente (notice, youtube, tiktok, etc.)

    Returns:
        Lista de categorías a excluir. Lista vacía si no hay exclusiones.
    """
    exclusions = load_exclusions_config(file_path)
    chunks_all = exclusions.get('chunks_all', {})
    return chunks_all.get(source_type, [])
