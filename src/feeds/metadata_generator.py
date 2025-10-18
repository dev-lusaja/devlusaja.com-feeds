import json
from pathlib import Path
from typing import Dict, Any
from utils.logger import log

def save_metadata_json(metadata: Dict[str, Any], output_dir: str = "assets") -> bool:
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
        output_path = assets_dir / "metadata.json"

        # Guardar JSON con formato legible
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        log(f"✅ Metadata guardado exitosamente en {output_path}")
        return True

    except Exception as e:
        log(f"❌ Error al guardar metadata: {e}")
        return False
