"""
Pipeline ETL chính – chạy bằng một lệnh:

  # Dataset chính thức Mekong Mobile (mặc định)
  python -m src.pipeline

  # Giới hạn số dòng (demo nhanh)
  python -m src.pipeline --limit 2000

  # Chỉ khi cần test file mẫu nhỏ
  python -m src.pipeline --sample

  # File lỗi để kiểm tra reject
  python -m src.pipeline --sample --file orders_bad.csv
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

from src.extract.extractor import extract_orders, extract_official
from src.quality.checks import run_all_quality_checks
from src.transform.transformer import transform_orders
from src.load.loader import init_db, load_dimensions, load_fact, load_rejects, get_connection
from src.config import DB_PATH


def run_pipeline(
    file_name: str = "orders_sample.csv",
    db_path: str | None = None,
    official: bool = True,
    limit: int | None = None,
) -> dict:
    """Chạy đầy đủ extract → quality → transform → load. Trả về báo cáo."""
    db = db_path or DB_PATH

    # 0. Khởi tạo schema (an toàn khi chạy lại)
    init_db(db)

    # 1. Extract
    if official:
        raw = extract_official(limit=limit)
        source_label = f"official (limit={limit})" if limit else "official"
    else:
        raw = extract_orders(file_name)
        source_label = file_name
    n_raw = len(raw)

    # 2. Quality (≥ 5 hàm kiểm)
    clean, reject, quality_report = run_all_quality_checks(raw)
    n_reject = load_rejects(reject, db)

    # 3. Transform + 4. Load
    if clean.empty:
        n_loaded = 0
    else:
        transformed = transform_orders(clean)
        mappings = load_dimensions(transformed, db)
        n_loaded = load_fact(transformed, mappings, db)

    # Thống kê cuối
    conn = get_connection(db)
    try:
        n_fact = conn.execute("SELECT COUNT(*) FROM fact_order_item").fetchone()[0]
        n_reject_total = conn.execute("SELECT COUNT(*) FROM reject_records").fetchone()[0]
    finally:
        conn.close()

    return {
        "source_file": source_label,
        "n_raw": n_raw,
        "n_clean": len(clean),
        "n_reject_this_run": n_reject,
        "n_loaded": n_loaded,
        "n_fact_total": n_fact,
        "n_reject_total": n_reject_total,
        "quality": quality_report,
    }


def main():
    parser = argparse.ArgumentParser(description="Smart CRM ETL Pipeline")
    parser.add_argument("--file", default="orders_sample.csv", help="File trong data/mau/")
    parser.add_argument("--official", action="store_true", default=True, help="Dùng dataset chính thức (mặc định)")
    parser.add_argument("--sample", action="store_true", help="Dùng file mẫu nhỏ (chỉ khi test)")
    parser.add_argument("--limit", type=int, default=None, help="Giới hạn số dòng (khi --official)")
    parser.add_argument("--db", default=None, help="Đường dẫn DB")
    args = parser.parse_args()

    print("=" * 60)
    print("Smart CRM – Data Warehouse ETL Pipeline")
    print("=" * 60)

    use_official = not args.sample
    report = run_pipeline(
        file_name=args.file,
        db_path=args.db,
        official=use_official,
        limit=args.limit,
    )

    print(f"\nNguồn        : {report['source_file']}")
    print(f"Dòng thô     : {report['n_raw']}")
    print(f"Dòng sạch    : {report['n_clean']}")
    print(f"Dòng reject  : {report['n_reject_this_run']}")
    print(f"Dòng nạp     : {report['n_loaded']}")
    print(f"Tổng fact    : {report['n_fact_total']}")
    print(f"Tổng reject  : {report['n_reject_total']}")
    print("\nBáo cáo chất lượng:")
    for q in report["quality"]:
        print(f"  - {q['check']}: {q['n_error']} lỗi ({q['error_rate']*100:.1f}%) – {q['reason']}")

    out = Path("data") / "last_pipeline_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nĐã ghi báo cáo → {out}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
