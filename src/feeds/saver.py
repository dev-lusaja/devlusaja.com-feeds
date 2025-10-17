import json
from datetime import datetime
from pathlib import Path
from utils.logger import log

def exits_feed(category):
    """Verifica si el feed para la categoría ya existe hoy."""
    file_path = feed_path_name(category)
    return file_path.exists()

def feed_path_name(category, output_dir: str = "feeds_data"):
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    Path(output_dir).mkdir(exist_ok=True)
    return Path(output_dir) / f"{category}_feed_{today_str}.json"

def save_feed(feed, category):
    """Guarda el feed completo en un archivo JSON."""
    feed_path = feed_path_name(category)
    with open(feed_path, 'w', encoding='utf-8') as f:
        json.dump(feed, f, indent=2, ensure_ascii=False, default=str)
    log(f"✅ Guardado en {feed_path}")

    return feed_path
