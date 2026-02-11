import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

MYSQL_HOST = os.getenv('MYSQL_HOST')
MYSQL_PORT = os.getenv('MYSQL_PORT')
MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASS = os.getenv('MYSQL_PASS')
MYSQL_DB = os.getenv('MYSQL_DB')


WORK_PATH = os.getenv('WORK_PATH')
DOMAIN_NAME = os.getenv('DOMAIN_NAME')
MAX_WORKERS = int(os.getenv('MAX_WORKERS', '3'))
QUEUE_NAME = os.getenv('QUEUE_NAME', 'queue:vmaf_jobs')
BLPOP_TIMEOUT = int(os.getenv('BLPOP_TIMEOUT', '20'))  # seconds
ROI = os.getenv('ROI', '0,0,500,300')  # Default full HD

CONFIG_FOLDER = "profiles/cpu"

VMAF_MODEL_PATH = "model/vmaf_v0.6.1.json"
VMAF_4K_MODEL_PATH = "model/vmaf_4k_v0.6.1.json"
VMAF_JSON_PATH = "vmaf.json"

# Các tham số liên quan đến Situation Segmenter
SEGMENTER_SCAN_STEP_SECONDS = float(os.getenv("SEGMENTER_SCAN_STEP_SECONDS", 5.0))
SEGMENTER_TRACK_STEP_SECONDS = float(os.getenv("SEGMENTER_TRACK_STEP_SECONDS", 2.0))
SEGMENTER_TIME_TOLERANCE_SECONDS = float(os.getenv("SEGMENTER_TIME_TOLERANCE_SECONDS", 1.5))
SEGMENTER_MIN_SEGMENT_DURATION_SECONDS = float(os.getenv("SEGMENTER_MIN_SEGMENT_DURATION_SECONDS", 1.0))