import os
from pathlib import Path
from utils.logger import log

def cleanup_json_files(feeds_dir: str = "feeds_data") -> int:
    """
    Elimina todos los archivos JSON del directorio de feeds.
    Mantiene el archivo feeds_dataframe.csv y feeds_dataframe.json

    Args:
        feeds_dir: Directorio donde se encuentran los archivos JSON

    Returns:
        Número de archivos eliminados
    """
    feeds_path = Path(feeds_dir)

    if not feeds_path.exists():
        return 0

    # Archivos a mantener
    keep_files = {'feeds_dataframe.csv', 'feeds_dataframe.json'}

    deleted_count = 0
    try:
        for json_file in feeds_path.glob("*.json"):
            if json_file.name not in keep_files:
                json_file.unlink()
                deleted_count += 1

        return deleted_count
    except Exception as e:
        log(f"❌ Error al limpiar archivos JSON: {e}")
        return deleted_count
