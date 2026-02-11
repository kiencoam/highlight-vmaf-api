import os
import logging
from logging.handlers import TimedRotatingFileHandler

def setup_logger(name, log_file, level=logging.DEBUG):
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Tránh tạo handler nhiều lần nếu hàm được gọi lại
    if logger.hasHandlers():
        return logger

    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    # 1. Định dạng chung cho log
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # 2. Handler ghi ra FILE (xoay vòng theo ngày)
    file_handler = TimedRotatingFileHandler(
        log_file, when='midnight', interval=1, backupCount=7, encoding='utf-8', utc=True
    )
    file_handler.suffix = '%Y%m%d'
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 3. Handler ghi ra MÀN HÌNH (Console)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger

log_file_path = 'logs/app.log'
logger = setup_logger("highlight-vmaf-api", log_file_path)

# Test thử
logger.info("Hệ thống bắt đầu chạy...")