from mysql.connector import Error
from database.connection import MySQLConnectionPool
from config.log import logger


class DBAccess:
    def __init__(self):
        self.pool = MySQLConnectionPool()

    def execute_query(self, query, params=None):
        connection = self.pool.get_connection()
        if connection is None:
            return None
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(query, params)
            return cursor.fetchall()
        except Error as e:
            logger.error(f"Error executing query: {e}")
            return None
        finally:
            cursor.close()
            connection.close()

    def execute_update(self, query, params=None):
        connection = self.pool.get_connection()
        if connection is None:
            return False
        cursor = connection.cursor()
        try:
            cursor.execute(query, params)
            connection.commit()
            return True
        except Error as e:
            logger.error(f"Error executing update: {e}")
            return False
        finally:
            cursor.close()
            connection.close()

    ############################################################################
    def _build_filter_query(self, status, query):
        """
        Hàm nội bộ để tạo câu lệnh WHERE và params động.
        Giúp đồng bộ logic lọc giữa hàm get list và hàm count.
        """
        conditions = []
        params = []

        # 1. Lọc theo Status (So sánh bằng)
        if status is not None:
            conditions.append("status = %s")
            params.append(status)

        # 2. Lọc theo Title (Tìm kiếm gần đúng - LIKE)
        if query:
            conditions.append("title LIKE %s ")
            params.append(f"%{query}%") # Thêm % để tìm kiếm chứa chuỗi

        # Ghép các điều kiện lại bằng AND
        where_clause = ""
        if conditions:
            where_clause = " WHERE " + " AND ".join(conditions)
            
        return where_clause, params

    def get_job_by_id(self, job_id):
        sql = "SELECT * FROM video_info WHERE id = %s and status = 0"
        
        # Sử dụng 'with' để đảm bảo connection luôn được trả lại pool
        try:
            with self.pool.get_connection() as connection:
                if not connection:
                    logger.error("Could not get connection from pool")
                    return None
                
                with connection.cursor(dictionary=True) as cursor:
                    cursor.execute(sql, (job_id,))
                    result = cursor.fetchone() # Fetchone hiệu quả hơn fetchall()[0]
                    return result
                    
        except Error as e:
            logger.error(f"Database error in get_job_by_id: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in get_job_by_id: {e}")
            return None
        
    def insert_video_info(self, original_url, highlight_url, title):
        sql = "INSERT INTO video_info (original_url, highlight_url, title, status) VALUES (%s, %s, %s, 0)"
        
        try:
            # Sử dụng context manager (with) để quản lý connection và cursor an toàn
            with self.pool.get_connection() as connection:
                if not connection:
                    return None
                
                with connection.cursor() as cursor:
                    cursor.execute(sql, (original_url, highlight_url, title))
                    connection.commit()
                    
                    # Lấy ID vừa được sinh ra
                    new_id = cursor.lastrowid
                    
                    # Trả về ID hoặc Dict chứa thông tin
                    return {
                        "id": new_id,
                        "original_url": original_url,
                        "highlight_url": highlight_url,
                        "title": title,
                        "status": 0
                    }

        except Error as e:
            logger.error(f"Error executing insert: {e}")
            return None
        
    def get_video_page(self, page=1, size=10, order_by='id', order_direction='desc', 
                       status=None, query=None):
        
        # 1. Validate cột sort (Chống SQL Injection)
        valid_columns = ["id", "title", "status", "original_url", "highlight_url"]
        if order_by not in valid_columns:
            order_by = "id"
        if order_direction.lower() not in ["asc", "desc"]:
            order_direction = "desc"

        # 2. Lấy điều kiện lọc từ hàm helper
        where_clause, params = self._build_filter_query(status, query)

        # 3. Xây dựng câu SQL hoàn chỉnh
        sql = f"SELECT * FROM video_info{where_clause} ORDER BY {order_by} {order_direction}"

        # 4. Tính toán phân trang
        limit = int(size)
        offset = (int(page) - 1) * limit
        
        sql += " LIMIT %s OFFSET %s"
        # Lưu ý: params của WHERE phải đứng trước params của LIMIT/OFFSET
        params.extend([limit, offset])

        try:
            with self.pool.get_connection() as connection:
                if not connection:
                    return []
                with connection.cursor(dictionary=True) as cursor:
                    cursor.execute(sql, tuple(params))
                    return cursor.fetchall()
        except Error as e:
            logger.error(f"Error fetching video page: {e}")
            return []
        
    def get_video_count(self, query=None, status=None):
        
        # 1. Lấy điều kiện lọc (tái sử dụng logic để đảm bảo nhất quán)
        where_clause, params = self._build_filter_query(status, query)
        
        # 2. Xây dựng câu SQL đếm
        sql = f"SELECT COUNT(*) as total FROM video_info{where_clause}"

        try:
            with self.pool.get_connection() as connection:
                if not connection:
                    return 0
                with connection.cursor(dictionary=True) as cursor:
                    cursor.execute(sql, tuple(params))
                    result = cursor.fetchone()
                    return result['total'] if result else 0
        except Error as e:
            logger.error(f"Error counting videos: {e}")
            return 0
        
    def get_highlight_page(self, video_id, page=1, size=10, order_by='id', order_direction='desc'):
        """
        Lấy danh sách stats của một video cụ thể.
        :param video_id: BẮT BUỘC.
        """
        # 0. Kiểm tra tham số bắt buộc
        if not video_id:
            logger.error("get_video_stats: video_id is required")
            return []

        # 1. Whitelist các cột được phép sort (Bảo mật)
        valid_columns = [
            "id", "video_id", "vmaf_mean", "vmaf_min", 
            "vmaf_max", "duration", "start_time", "end_time"
        ]
        
        if order_by not in valid_columns:
            order_by = "id"
            
        if order_direction.lower() not in ["asc", "desc"]:
            order_direction = "desc"

        # 2. Xây dựng Query
        # Lưu ý: video_id là bắt buộc nên ta để cứng trong WHERE
        sql = f"SELECT * FROM video_stats WHERE video_id = %s ORDER BY {order_by} {order_direction}"

        # 3. Phân trang
        limit = int(size)
        offset = (int(page) - 1) * limit
        
        sql += " LIMIT %s OFFSET %s"
        
        # 4. Thực thi
        try:
            with self.pool.get_connection() as connection:
                if not connection:
                    return []
                
                with connection.cursor(dictionary=True) as cursor:
                    # Truyền tham số theo đúng thứ tự: video_id -> limit -> offset
                    cursor.execute(sql, (video_id, limit, offset))
                    return cursor.fetchall()

        except Error as e:
            logger.error(f"Error fetching video_stats: {e}")
            return []

    def get_highlight_count(self, video_id):
        """
        Đếm tổng số dòng stats của một video_id (dùng để tính phân trang).
        """
        if not video_id:
            return 0
            
        sql = "SELECT COUNT(*) as total FROM video_stats WHERE video_id = %s"

        try:
            with self.pool.get_connection() as connection:
                if not connection:
                    return 0
                
                with connection.cursor(dictionary=True) as cursor:
                    cursor.execute(sql, (video_id,))
                    result = cursor.fetchone()
                    return result['total'] if result else 0
                    
        except Error as e:
            logger.error(f"Error counting video_stats: {e}")
            return 0