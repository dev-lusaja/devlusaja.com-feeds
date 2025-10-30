import os
import subprocess
from pathlib import Path
from datetime import datetime
from utils.logger import log

def create_mysql_backup():
    """
    Crea un backup de MySQL con la fecha actual y mantiene solo los 2 backups más recientes.

    Returns:
        Path del archivo de backup creado, o None si hubo error
    """
    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"backup_{timestamp}.sql"

    db_user = os.getenv('DB_USER', 'feeds_user')
    db_password = os.getenv('DB_PASSWORD', 'feeds_password')
    db_name = os.getenv('DB_NAME', 'feeds_db')
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '3306')

    try:
        # Crear backup usando mysqldump directamente
        cmd = [
            'mysqldump',
            f'--host={db_host}',
            f'--port={db_port}',
            f'--user={db_user}',
            f'--password={db_password}',
            '--single-transaction',
            '--quick',
            '--lock-tables=false',
            '--skip-ssl',
            db_name
        ]

        with open(backup_file, 'w') as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)

        if result.returncode == 0:
            # Mantener solo los 2 backups más recientes
            backups = sorted(backup_dir.glob("backup_*.sql"), key=lambda x: x.stat().st_mtime, reverse=True)

            if len(backups) > 2:
                for old_backup in backups[2:]:
                    old_backup.unlink()

            return str(backup_file)
        else:
            log(f"❌ Error al crear backup: {result.stderr}")
            return None

    except Exception as e:
        log(f"❌ Error al crear backup: {e}")
        return None
