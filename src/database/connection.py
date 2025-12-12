import os
import sqlite3
from pathlib import Path
from typing import Optional
from utils.logger import log

class DatabaseConnection:
    """
    Gestiona la conexión a la base de datos SQLite.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Inicializa la conexión a SQLite.
        
        Args:
            db_path: Ruta al archivo de base de datos SQLite.
                    Si es None, usa SQLITE_DB_PATH del .env o 'data/feeds.db' por defecto.
        """
        if db_path is None:
            db_path = 'data/feeds.db'
        self.db_path = Path(db_path)
        self.connection = None
        
        # Crear directorio si no existe
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> Optional[sqlite3.Connection]:
        """
        Establece conexión con la base de datos SQLite.

        Returns:
            Objeto de conexión SQLite o None si falla
        """
        try:
            if self.connection is None:
                self.connection = sqlite3.connect(str(self.db_path))
                
                # Configurar row_factory para acceso por nombre de columna
                self.connection.row_factory = sqlite3.Row
                
                # Optimizaciones de SQLite
                self.connection.execute("PRAGMA journal_mode=WAL")
                self.connection.execute("PRAGMA synchronous=NORMAL")
                self.connection.execute("PRAGMA foreign_keys=ON")
                self.connection.execute("PRAGMA cache_size=10000")
                
                log(f"✅ Conectado a SQLite: {self.db_path}")
            return self.connection
        except sqlite3.Error as e:
            log(f"❌ Error al conectar a SQLite: {e}")
            return None

    def disconnect(self):
        """
        Cierra la conexión con la base de datos.
        """
        if self.connection:
            self.connection.close()
            self.connection = None
            log("🔌 Conexión a SQLite cerrada")

    def get_cursor(self):
        """
        Obtiene un cursor para ejecutar queries.

        Returns:
            Cursor SQLite o None si no hay conexión
        """
        if self.connection:
            return self.connection.cursor()
        else:
            log("⚠️ No hay conexión activa para obtener cursor")
            return None

    def commit(self):
        """
        Hace commit de las transacciones pendientes.
        """
        if self.connection:
            self.connection.commit()

    def rollback(self):
        """
        Hace rollback de las transacciones pendientes.
        """
        if self.connection:
            self.connection.rollback()

    def __enter__(self):
        """
        Soporte para context manager (with statement).
        """
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Cierre automático al salir del context manager.
        """
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.disconnect()
