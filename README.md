# Smart CRM – Data Warehouse (Track DA)

Hệ thống kho dữ liệu bán hàng cho chuỗi **Mekong Mobile**: pipeline ETL 3 pha, Star Schema, bảng reject, dashboard HTML 2 biểu đồ.

- **Luồng:** L6 – Kho dữ liệu bán hàng và báo cáo doanh thu  
- **Track:** DA  
- **SV:** Hồ Thị Ngọc Quỳnh – 2374802010426  
- **Nguồn dữ liệu:** Dataset chính thức Mekong Mobile (`data/official/`)

## Yêu cầu môi trường
- Python 3.10+  
- pip  

## Cài đặt & chạy (mỗi bước = 1 lệnh)

```bash
git clone <URL-repo> .
cd smart-crm-dw

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env

# Pipeline – dataset chính thức (mặc định)
python -m src.pipeline

# Giới hạn 2000 dòng (chạy nhanh khi demo)
python -m src.pipeline --limit 2000

# Chạy LẠI lần 2 – kiểm tra không nhân đôi
python -m src.pipeline --limit 2000

# Dashboard
python -m src.dashboard
python -m src.dashboard --simulate empty --out data/dashboard_empty.html
python -m src.dashboard --simulate error  --out data/dashboard_error.html
```

## Kiểm thử
```bash
pytest tests/ -v
```
Phải PASS toàn bộ.

## Kiểm tra đúng
1. Lần 1: fact có dữ liệu, reject ghi dòng lỗi (nếu có).  
2. Lần 2: **số dòng fact không tăng**.  
3. Mở `data/dashboard_report.html` thấy KPI + 2 biểu đồ.  
4. `pytest` → 4 passed.

## Cấu trúc
```
docs/          srs, thay-doi-thiet-ke, ai-disclosure, architecture, diagrams/
src/extract/   join dataset chính thức (orders + items + products + stores)
src/quality/   ≥ 5 hàm kiểm (trả n_error + rate)
src/transform/ tính Net Revenue, COGS, Gross Profit
src/load/      upsert dim + INSERT OR REPLACE fact
src/pipeline.py
src/dashboard.py
sql/001_schema.sql
data/official/ orders_2024_2026, order_items, products, stores
tests/
```

## Dataset chính thức
| File | Vai trò |
|------|---------|
| orders_2024_2026.csv | Header đơn hàng (~26.000) |
| order_items.csv | Dòng sản phẩm (~35.700) |
| products.csv | Dimension sản phẩm |
| stores.csv | Dimension cửa hàng |

Pipeline mặc định join 4 file trên. Không cần file mẫu.

## Quy tắc nghiệp vụ
1. Net Revenue = qty × price − discount  
2. COGS = qty × unit_cost  
3. Gross Profit = Net Revenue − COGS  
4. Từ chối: ngày sai, giá < 1000, qty ∉ [1,100], discount > 50% gross  
5. Nạp lại không nhân đôi  

## Tag
```bash
git tag -a v0.2 -m "Bai tap 2"
git push origin v0.2
```
