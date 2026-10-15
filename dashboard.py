"""
Dashboard đơn giản – tạo báo cáo HTML + biểu đồ PNG.
Xử lý 3 trạng thái: đang truy vấn · rỗng · lỗi kết nối.
Chạy: python -m src.dashboard
"""
from __future__ import annotations
import base64
import io
import sqlite3
from pathlib import Path
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src.config import DB_PATH
from src.load.loader import get_connection


def _fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=120)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def query_kpis(conn: sqlite3.Connection) -> dict:
    row = conn.execute("""
        SELECT
            COALESCE(SUM(net_revenue), 0),
            COALESCE(COUNT(DISTINCT order_id), 0),
            COALESCE(SUM(gross_profit), 0),
            COALESCE(SUM(quantity), 0)
        FROM fact_order_item
    """).fetchone()
    net_rev, n_orders, gross_profit, total_qty = row
    aov = net_rev / n_orders if n_orders else 0
    return {
        "net_revenue": net_rev,
        "n_orders": n_orders,
        "aov": aov,
        "gross_profit": gross_profit,
        "total_qty": total_qty,
    }


def chart_revenue_by_channel(conn: sqlite3.Connection) -> str | None:
    """Biểu đồ 1: Doanh thu thuần theo kênh bán (câu hỏi: Kênh nào mang lại doanh thu cao nhất?)"""
    df = pd.read_sql_query("""
        SELECT c.channel_name, SUM(f.net_revenue) AS revenue
        FROM fact_order_item f
        JOIN dim_channel c ON f.channel_key = c.channel_key
        GROUP BY c.channel_name
        ORDER BY revenue DESC
    """, conn)
    if df.empty:
        return None
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.barh(df["channel_name"], df["revenue"] / 1e6, color="#2563eb")
    ax.set_xlabel("Doanh thu thuần (triệu VND)")
    ax.set_title("Doanh thu thuần theo kênh bán")
    # Mốc tham chiếu: trung bình
    avg = df["revenue"].mean() / 1e6
    ax.axvline(avg, color="red", linestyle="--", label=f"Trung bình {avg:.1f}M")
    ax.legend()
    b64 = _fig_to_base64(fig)
    plt.close(fig)
    return b64


def chart_top_products(conn: sqlite3.Connection) -> str | None:
    """Biểu đồ 2: Top sản phẩm theo doanh thu (câu hỏi: Sản phẩm nào bán chạy nhất?)"""
    df = pd.read_sql_query("""
        SELECT p.product_name, SUM(f.net_revenue) AS revenue, SUM(f.quantity) AS qty
        FROM fact_order_item f
        JOIN dim_product p ON f.product_key = p.product_key
        GROUP BY p.product_name
        ORDER BY revenue DESC
        LIMIT 10
    """, conn)
    if df.empty:
        return None
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.barh(df["product_name"], df["revenue"] / 1e6, color="#16a34a")
    ax.set_xlabel("Doanh thu thuần (triệu VND)")
    ax.set_title("Top sản phẩm theo doanh thu thuần")
    b64 = _fig_to_base64(fig)
    plt.close(fig)
    return b64


def generate_report(db_path: str | None = None, simulate: str | None = None) -> str:
    """
    Tạo HTML report.
    simulate: None | 'empty' | 'error'  – để demo 3 trạng thái.
    """
    db = db_path or DB_PATH
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # --- Trạng thái: đang truy vấn (giả lập bằng thông báo) ---
    status_block = f"<p class='status loading'>Đang truy vấn kho dữ liệu… ({ts})</p>"

    if simulate == "error":
        # Trạng thái lỗi kết nối – KHÔNG in chuỗi connection
        html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
        <title>Smart CRM Dashboard</title>
        <style>
        body{{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem}}
        .error{{background:#fef2f2;border:1px solid #fecaca;padding:1.5rem;border-radius:8px;color:#991b1b}}
        button{{margin-top:1rem;padding:.5rem 1rem;cursor:pointer}}
        </style></head><body>
        <h1>Smart CRM – Dashboard Doanh thu</h1>
        <div class="error">
          <strong>Không thể kết nối tới Kho dữ liệu.</strong><br>
          Vui lòng kiểm tra đường truyền hoặc liên hệ quản trị viên.
          <br><button onclick="location.reload()">Thử lại</button>
        </div>
        <p><small>Thời điểm: {ts}</small></p>
        </body></html>"""
        return html

    try:
        conn = get_connection(db)
        # Kiểm tra bảng tồn tại
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        if "fact_order_item" not in tables:
            raise sqlite3.OperationalError("missing table")

        kpis = query_kpis(conn)
        chart1 = chart_revenue_by_channel(conn)
        chart2 = chart_top_products(conn)
        conn.close()
    except Exception:
        # Lỗi kết nối / schema
        html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
        <title>Smart CRM Dashboard</title>
        <style>
        body{{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem}}
        .error{{background:#fef2f2;border:1px solid #fecaca;padding:1.5rem;border-radius:8px;color:#991b1b}}
        button{{margin-top:1rem;padding:.5rem 1rem;cursor:pointer}}
        </style></head><body>
        <h1>Smart CRM – Dashboard Doanh thu</h1>
        <div class="error">
          <strong>Không thể kết nối tới Kho dữ liệu.</strong><br>
          Vui lòng kiểm tra đường truyền hoặc liên hệ quản trị viên.
          <br><button onclick="location.reload()">Thử lại</button>
        </div>
        <p><small>Thời điểm: {ts}</small></p>
        </body></html>"""
        return html

    # --- Trạng thái rỗng ---
    if kpis["n_orders"] == 0 or simulate == "empty":
        html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
        <title>Smart CRM Dashboard</title>
        <style>
        body{{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem}}
        .empty{{background:#f0f9ff;border:1px solid #bae6fd;padding:1.5rem;border-radius:8px;color:#0c4a6e}}
        .kpi{{display:inline-block;background:#f8fafc;border:1px solid #e2e8f0;padding:1rem 1.5rem;margin:.5rem;border-radius:8px;min-width:140px}}
        .kpi b{{display:block;font-size:1.4rem}}
        </style></head><body>
        <h1>Smart CRM – Dashboard Doanh thu</h1>
        <div class="empty">
          <strong>Không tìm thấy dữ liệu giao dịch.</strong><br>
          Chưa có dữ liệu trong khoảng thời gian / bộ lọc hiện tại.
          (Phân biệt: hệ thống đã kết nối thành công nhưng kết quả rỗng.)
        </div>
        <div>
          <div class="kpi"><span>Tổng doanh thu</span><b>0 ₫</b></div>
          <div class="kpi"><span>Số đơn hàng</span><b>0</b></div>
          <div class="kpi"><span>AOV</span><b>0 ₫</b></div>
          <div class="kpi"><span>Lợi nhuận gộp</span><b>0 ₫</b></div>
        </div>
        <p><small>Nguồn: fact_order_item · Thời điểm: {ts}</small></p>
        </body></html>"""
        return html

    # --- Trạng thái có dữ liệu ---
    def fmt(v):
        return f"{v:,.0f} ₫"

    charts_html = ""
    if chart1:
        charts_html += f'<h2>1. Doanh thu theo kênh bán</h2><p>Câu hỏi: <em>Kênh nào mang lại doanh thu cao nhất?</em></p><img src="data:image/png;base64,{chart1}" alt="chart1"/><p><small>Nguồn: fact_order_item JOIN dim_channel · Mốc: đường đỏ = trung bình · {ts}</small></p>'
    if chart2:
        charts_html += f'<h2>2. Top sản phẩm theo doanh thu</h2><p>Câu hỏi: <em>Sản phẩm nào đóng góp doanh thu nhiều nhất?</em></p><img src="data:image/png;base64,{chart2}" alt="chart2"/><p><small>Nguồn: fact_order_item JOIN dim_product · {ts}</small></p>'

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
    <title>Smart CRM Dashboard</title>
    <style>
    body{{font-family:system-ui,sans-serif;max-width:960px;margin:2rem auto;padding:0 1rem;color:#1e293b}}
    .kpi{{display:inline-block;background:#f8fafc;border:1px solid #e2e8f0;padding:1rem 1.5rem;margin:.4rem;border-radius:8px;min-width:150px}}
    .kpi span{{font-size:.85rem;color:#64748b}}
    .kpi b{{display:block;font-size:1.35rem;margin-top:.25rem}}
    img{{max-width:100%;border:1px solid #e2e8f0;border-radius:8px}}
    h1{{margin-bottom:.25rem}}
    .meta{{color:#64748b;font-size:.9rem}}
    </style></head><body>
    <h1>Smart CRM – Dashboard Doanh thu</h1>
    <p class="meta">Nguồn dữ liệu thật từ kho · Cập nhật: {ts}</p>
    <div>
      <div class="kpi"><span>Tổng doanh thu thuần</span><b>{fmt(kpis['net_revenue'])}</b></div>
      <div class="kpi"><span>Số đơn hàng</span><b>{kpis['n_orders']}</b></div>
      <div class="kpi"><span>AOV</span><b>{fmt(kpis['aov'])}</b></div>
      <div class="kpi"><span>Lợi nhuận gộp</span><b>{fmt(kpis['gross_profit'])}</b></div>
    </div>
    {charts_html}
    </body></html>"""
    return html


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--simulate", choices=["empty", "error"], default=None)
    parser.add_argument("--out", default="data/dashboard_report.html")
    args = parser.parse_args()

    print("Đang tạo dashboard report…")
    html = generate_report(simulate=args.simulate)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"Đã ghi → {out.resolve()}")
    if args.simulate:
        print(f"(Chế độ giả lập trạng thái: {args.simulate})")


if __name__ == "__main__":
    main()
