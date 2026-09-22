"""
Odoo Avg Costing Agent — Tự động demo sh_warehouse_avg_costing
Chạy: python agent_avg_costing.py --gemini-key YOUR_KEY
"""

from __future__ import annotations
import argparse
import asyncio
import os

ODOO_URL = "https://demo19.openerp.vn/"
ODOO_DB = "KETOANCE"
ODOO_USER = "admin"
ODOO_PASSWORD = "admin"

TASK = """
Bạn là AI agent thao tác Odoo 19. Thực hiện theo thứ tự các bước sau.
Sau mỗi bước báo cáo kết quả trước khi tiếp tục.

URL Odoo: {url}
Database: {db}
User: {user}
Password: {password}

=== BƯỚC 1: ĐĂNG NHẬP ===
- Mở {url}
- Nếu có màn hình chọn database, chọn "{db}"
- Nhập user: {user}, password: {password}
- Xác nhận đã vào được trang chủ Odoo

=== BƯỚC 2: CẤU HÌNH AVERAGE COSTING ===
- Vào Inventory → Configuration → Settings
- Tìm mục "Costing Method" hoặc "Valuation"
- Đảm bảo chọn "Average Cost (AVCO)"
- Lưu settings

=== BƯỚC 3: TẠO DANH MỤC SẢN PHẨM AVCO ===
- Vào Inventory → Configuration → Product Categories
- Tạo category mới tên "Vật tư AVCO"
- Costing Method: Average Cost (AVCO)
- Account Stock Valuation: chọn tài khoản phù hợp nếu có
- Lưu lại

=== BƯỚC 4: TẠO 3 SẢN PHẨM ===
Vào Inventory → Products → Products → New, tạo lần lượt:

Sản phẩm 1:
- Tên: Sắt hộp 40x40
- Product Type: Storable Product
- Category: Vật tư AVCO
- Purchase Price: 25000
- Unit: m (mét)
- Lưu lại

Sản phẩm 2:
- Tên: Tấm Alu 1220x2440
- Product Type: Storable Product
- Category: Vật tư AVCO
- Purchase Price: 850000
- Unit: Tấm
- Lưu lại

Sản phẩm 3:
- Tên: Module LED SMD 5050
- Product Type: Storable Product
- Category: Vật tư AVCO
- Purchase Price: 4500
- Unit: Cái
- Lưu lại

=== BƯỚC 5: TẠO NHÀ CUNG CẤP ===
- Vào Contacts → New
- Tên: Công ty Vật Tư Xây Dựng Miền Nam
- Company Type: Company
- Phone: 0281234567
- Email: vlxd.miennam@gmail.com
- Lưu lại

=== BƯỚC 6: TẠO PURCHASE ORDER LẦN 1 (GIÁ THẤP) ===
- Vào Purchase → Orders → Purchase Orders → New
- Vendor: Công ty Vật Tư Xây Dựng Miền Nam
- Thêm 3 dòng sản phẩm:
  * Sắt hộp 40x40 | SL: 100m | Giá: 22000
  * Tấm Alu 1220x2440 | SL: 10 tấm | Giá: 800000
  * Module LED SMD 5050 | SL: 500 cái | Giá: 4000
- Confirm Order
- Vào Receive Products → Validate (nhận hàng đầy đủ)
- Ghi nhận: Giá vốn bình quân sau lần nhập 1

=== BƯỚC 7: XEM GIÁ VỐN BÌNH QUÂN SAU LẦN 1 ===
- Vào từng sản phẩm (Sắt hộp, Alu, LED)
- Kiểm tra tab "Purchase" hoặc xem Cost
- Chụp màn hình hoặc ghi nhận giá vốn hiện tại

=== BƯỚC 8: TẠO PURCHASE ORDER LẦN 2 (GIÁ CAO HƠN) ===
- Vào Purchase → Orders → Purchase Orders → New
- Vendor: Công ty Vật Tư Xây Dựng Miền Nam
- Thêm 3 dòng sản phẩm:
  * Sắt hộp 40x40 | SL: 50m | Giá: 28000
  * Tấm Alu 1220x2440 | SL: 5 tấm | Giá: 920000
  * Module LED SMD 5050 | SL: 300 cái | Giá: 5200
- Confirm Order
- Receive Products → Validate
- Ghi nhận: Giá vốn bình quân sau lần nhập 2 (phải thay đổi)

=== BƯỚC 9: XEM BÁO CÁO WAREHOUSE AVG COSTING ===
- Vào menu Inventory → Reporting hoặc tìm "Warehouse Avg Costing"
- Hoặc vào menu sh_warehouse_avg_costing nếu có menu riêng
- Xem báo cáo giá vốn bình quân theo warehouse
- Kiểm tra 3 sản phẩm đã tạo có đúng giá bình quân không

=== BƯỚC 10: TÍNH KIỂM TRA ===
Giá vốn bình quân đúng phải là:
- Sắt hộp 40x40: (100m x 22000 + 50m x 28000) / 150m = 24000 VND/m
- Tấm Alu: (10 x 800000 + 5 x 920000) / 15 = 840000 VND/tấm
- Module LED: (500 x 4000 + 300 x 5200) / 800 = 4450 VND/cái

Kiểm tra xem module tính đúng không và báo cáo kết quả.

Nếu gặp lỗi ở bất kỳ bước nào, mô tả lỗi cụ thể và tiếp tục bước tiếp theo nếu có thể.
""".strip()


async def run(gemini_key: str, headless: bool = False):
    try:
        from browser_use import Agent
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError:
        print("Thiếu thư viện. Chạy:")
        print("  pip install browser-use playwright langchain-google-genai")
        print("  playwright install chromium")
        return

    os.environ["GEMINI_API_KEY"] = gemini_key

    llm = ChatGoogleGenerativeAI(
        model="gemini-3.6-flash",
        google_api_key=gemini_key,
        temperature=0.1,
    )

    task = TASK.format(
        url=ODOO_URL,
        db=ODOO_DB,
        user=ODOO_USER,
        password=ODOO_PASSWORD,
    )

    print("=" * 60)
    print("Odoo Avg Costing Agent")
    print(f"URL: {ODOO_URL} | DB: {ODOO_DB}")
    print("=" * 60)

    from browser_use import BrowserConfig
    browser_config = BrowserConfig(
        headless=headless,
        disable_security=True,
        extra_chromium_args=[
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
        ]
    )
    agent = Agent(
        task=task,
        llm=llm,
        max_actions_per_step=10,
        browser_config=browser_config,
    )

    result = await agent.run(max_steps=150)
    print("\n" + "=" * 60)
    print("KẾT QUẢ:")
    print(result)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gemini-key", required=True, help="Gemini API key")
    parser.add_argument("--headless", action="store_true", help="Chạy browser ngầm")
    args = parser.parse_args()
    asyncio.run(run(args.gemini_key, args.headless))


if __name__ == "__main__":
    main()
