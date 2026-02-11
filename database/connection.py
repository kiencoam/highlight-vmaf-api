from mysql.connector import pooling, Error
from config.settings import *
from config.log import logger

class MySQLConnectionPool:
    def __init__(self):
        try:
            # Khởi tạo MySQLConnectionPool
            self.pool = pooling.MySQLConnectionPool(
                pool_name="mypool",
                pool_size=2,
                pool_reset_session=True,
                host=MYSQL_HOST,
                port=MYSQL_PORT,
                user=MYSQL_USER,
                password=MYSQL_PASS,
                database=MYSQL_DB
            )
        except Error as e:
            logger.error(f"Error while connecting to MySQL using Connection pool: {e}")

    def get_connection(self):
        try:
            return self.pool.get_connection()  # Trả về kết nối từ pool
        except Error as e:
            logger.error(f"Error getting connection from pool: {e}")
            return None
