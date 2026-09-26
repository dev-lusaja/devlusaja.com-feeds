import json
from pathlib import Path
from typing import Dict, Any
from utils.logger import log
from config.loader import SEPARATE_SOURCE_TYPES, get_db_path
from database.connection import DatabaseConnection
from database.operations import get_metadata_from_db, create_feeds_table
from feeds.chunk_generator import generate_feed_chunks
from feeds.category_chunk_generator import generate_category_chunks

def generate_all_metadata(db, feeds_config, months_back=None, max_chunks=None, output_dir: str = "assets", source_type: str = None) -> bool:
    """Genera metadata.json (feeds normales) o {source_type}-metadata.json (SEPARATE_SOURCE_TYPES, desde su propia BD)."""
    metadata = get_metadata_from_db(db, feeds_config, months_back=months_back, max_chunks=max_chunks, source_type=source_type)
    filename = f"{source_type}-metadata.json" if source_type else "metadata.json"
    return bool(metadata) and save_metadata_json(metadata, output_dir, filename)

def generate_separate_assets(feeds_config, max_chunks=None, items_per_chunk: int = 30, output_dir: str = "assets"):
    """Metadata + chunks de cada SEPARATE_SOURCE_TYPES desde su propia BD, con su propia ventana de fechas."""
    for source_type, period in SEPARATE_SOURCE_TYPES.items():
        with DatabaseConnection(get_db_path(source_type)) as db:
            create_feeds_table(db)  # la BD puede no existir aún (p. ej. no está en Drive todavía)
            generate_all_metadata(db, feeds_config, months_back=period, max_chunks=max_chunks, output_dir=output_dir, source_type=source_type)
            generate_feed_chunks(db, output_dir=output_dir, items_per_chunk=items_per_chunk, months_back=period, max_chunks=max_chunks)
            generate_category_chunks(db, output_dir=output_dir, items_per_chunk=items_per_chunk, months_back=period, max_chunks=max_chunks)

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
