import os
import mysql.connector
from mysql.connector import Error
from typing import Optional
from utils.logger import log

class DatabaseConnection:
    """
    Gestiona la conexión a la base de datos MySQL.
    """

    def __init__(self):
        self.host = os.getenv('DB_HOST', 'localhost')
        self.port = os.getenv('DB_PORT', '3306')
        self.database = os.getenv('DB_NAME', 'feeds_db')
        self.user = os.getenv('DB_USER', 'feeds_user')
        self.password = os.getenv('DB_PASSWORD', 'feeds_password')
        self.connection = None

    def connect(self) -> Optional[mysql.connector.MySQLConnection]:
        """
        Establece conexión con la base de datos.

        Returns:
            Objeto de conexión MySQL o None si falla
        """
        try:
            if self.connection is None or not self.connection.is_connected():
                self.connection = mysql.connector.connect(
                    host=self.host,
                    port=self.port,
                    database=self.database,
                    user=self.user,
                    password=self.password,
                    charset='utf8mb4',
                    collation='utf8mb4_unicode_ci'
                )
                log(f"✅ Conectado a MySQL en {self.host}:{self.port}/{self.database}")
            return self.connection
        except Error as e:
            log(f"❌ Error al conectar a MySQL: {e}")
            return None

    def disconnect(self):
        """
        Cierra la conexión con la base de datos.
        """
        if self.connection and self.connection.is_connected():
            self.connection.close()
            log("🔌 Conexión a MySQL cerrada")

    def get_cursor(self):
        """
        Obtiene un cursor para ejecutar queries.

        Returns:
            Cursor MySQL o None si no hay conexión
        """
        if self.connection and self.connection.is_connected():
            return self.connection.cursor(dictionary=True)
        else:
            log("⚠️ No hay conexión activa para obtener cursor")
            return None

    def commit(self):
        """
        Hace commit de las transacciones pendientes.
        """
        if self.connection and self.connection.is_connected():
            self.connection.commit()

    def rollback(self):
        """
        Hace rollback de las transacciones pendientes.
        """
        if self.connection and self.connection.is_connected():
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
