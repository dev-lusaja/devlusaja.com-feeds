import yaml
from pathlib import Path
from typing import List, Dict, Any

# sourceTypes con su propio proceso (--source-type), horario y metadata ({type}-metadata.json);
# quedan fuera de la corrida normal y de metadata.json
SEPARATE_SOURCE_TYPES = ('googlenews',)

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

def load_config(file_path: str) -> Dict[str, Any]:
    """
    Carga la configuración general desde el archivo YAML.

    Args:
        file_path: Ruta al archivo de configuración YAML

    Returns:
        Diccionario con la configuración general
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return data.get('config', {})

def get_feeds_months_back(file_path: str) -> int:
    """
    Obtiene el número de meses hacia atrás para filtrar feeds.

    Args:
        file_path: Ruta al archivo de configuración YAML

    Returns:
        Número de meses (por defecto 2 si no está configurado)
    """
    config = load_config(file_path)
    return config.get('feeds_months_back', 2)

def get_max_chunks_per_category(file_path: str) -> int:
    """
    Obtiene el número máximo de chunks a generar por categoría/tipo.

    Args:
        file_path: Ruta al archivo de configuración YAML

    Returns:
        Número máximo de chunks (None = sin límite, int > 0 = límite)
    """
    config = load_config(file_path)
    return config.get('max_chunks_per_category', None)
