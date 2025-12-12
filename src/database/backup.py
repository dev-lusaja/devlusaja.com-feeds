import os
import shutil
from pathlib import Path
from datetime import datetime
from utils.logger import log

def create_sqlite_backup():
    """
    Crea un backup de SQLite copiando el archivo de base de datos.
    Mantiene solo los 2 backups más recientes.

    Returns:
        Path del archivo de backup creado, o None si hubo error
    """
    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"feeds_{timestamp}.db"

    db_path = Path(os.getenv('SQLITE_DB_PATH', 'data/feeds.db'))

    try:
        # Copiar el archivo de base de datos
        shutil.copy2(db_path, backup_file)
        
        log(f"✅ Backup creado: {backup_file}")

        # Mantener solo los 2 backups más recientes
        backups = sorted(backup_dir.glob("feeds_*.db"), key=lambda x: x.stat().st_mtime, reverse=True)

        if len(backups) > 2:
            for old_backup in backups[2:]:
                old_backup.unlink()
                log(f"🗑️ Backup antiguo eliminado: {old_backup.name}")

        return str(backup_file)

    except Exception as e:
        log(f"❌ Error al crear backup: {e}")
        return None

