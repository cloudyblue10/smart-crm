"""Cấu hình hệ thống – đọc từ biến môi trường hoặc giá trị mặc định."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "data" / "warehouse.db"))
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data" / "mau")))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
REJECT_TABLE = os.getenv("REJECT_TABLE", "reject_records")

# Ngưỡng nghiệp vụ
MAX_DISCOUNT_RATIO = 0.5          # giảm giá không được vượt 50% gross
MIN_QUANTITY = 1
MAX_QUANTITY = 100
MIN_UNIT_PRICE = 1000             # VND
