import json
from pathlib import Path
from typing import Dict, Any
from utils.logger import log
from config.loader import SEPARATE_SOURCE_TYPES
from database.operations import get_metadata_from_db

def generate_all_metadata(db, feeds_config, months_back=None, max_chunks=None, output_dir: str = "assets") -> bool:
    """Genera metadata.json (feeds normales) y {type}-metadata.json por cada SEPARATE_SOURCE_TYPES."""
    ok = True
    for source_type in (None, *SEPARATE_SOURCE_TYPES):
        metadata = get_metadata_from_db(db, feeds_config, months_back=months_back, max_chunks=max_chunks, source_type=source_type)
        filename = f"{source_type}-metadata.json" if source_type else "metadata.json"
        ok = bool(metadata) and save_metadata_json(metadata, output_dir, filename) and ok
    return ok

def save_metadata_json(metadata: Dict[str, Any], output_dir: str = "assets", filename: str = "metadata.json") -> bool:
    """
    Guarda el metadata en un archivo JSON en la carpeta assets.

    Args:
        metadata: Diccionario con el metadata a guardar
        output_dir: Directorio donde guardar el archivo (por defecto 'assets')

    Returns:
        True si se guardó exitosamente, False en caso contrario
    """
    try:
        # Crear directorio si no existe
        assets_dir = Path(output_dir)
        assets_dir.mkdir(exist_ok=True)

        # Ruta del archivo
        output_path = assets_dir / filename

        # Guardar JSON con formato legible
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        return True

    except Exception as e:
        log(f"❌ Error al guardar metadata: {e}")
        return False
