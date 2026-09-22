"""
Odoo Demo Agent — Browser Use + Gemini Pro
Tự động thao tác Odoo theo kịch bản demo biển quảng cáo.

Cách dùng:
  python agent.py --url https://demo.bizapps.vn --user admin --password xxx --gemini-key xxx
"""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path

# ── Kịch bản demo biển quảng cáo ─────────────────────────────────────────────
DEMO_SCENARIOS = {
    "full": """
Bạn là AI agent thao tác Odoo 18. Thực hiện theo thứ tự:

1. Đăng nhập vào Odoo tại {url} với user {user} và password {password}

2. Tạo 2 Sales Team:
   - Vào CRM → Configuration → Sales Teams
   - Tạo team "KD - Nguồn công ty"
   - Tạo team "KD - Tự khai thác"

3. Tạo 8 khách hàng (vào Contacts → Contacts → New):
   - Công ty TNHH Thương Mại An Phú | MST: 0312345678 | ĐT: 0901234567 | Email: anphu@gmail.com | Địa chỉ: 123 Nguyễn Văn Linh, Q7, HCM
   - Công ty CP Truyền Thông Sáng Tạo | MST: 0398765432 | ĐT: 0912345678 | Email: sangtao@gmail.com | Địa chỉ: 45 Đinh Tiên Hoàng, Q1, HCM
   - Chuỗi Showroom An Nhiên | MST: 0387654321 | ĐT: 0923456789 | Email: annhien@gmail.com | Địa chỉ: 78 Xô Viết Nghệ Tĩnh, Bình Thạnh, HCM
   - Công ty TNHH Nội Thất Thủ Đức | MST: 0376543210 | ĐT: 0934567890 | Email: thuduc@gmail.com | Địa chỉ: 156 Võ Văn Ngân, Thủ Đức, HCM
   - Siêu Thị Điện Máy Phú Nhuận | MST: 0365432109 | ĐT: 0945678901 | Email: phunhuan@gmail.com | Địa chỉ: 234 Phan Xích Long, Phú Nhuận, HCM
   - Nhà Hàng Hải Sản Bình Dương | MST: 0354321098 | ĐT: 0956789012 | Email: binhduong@gmail.com | Địa chỉ: 89 Lê Hồng Phong, Bình Dương
   - Công ty CP Quảng Cáo Đại Việt | MST: 0343210987 | ĐT: 0967890123 | Email: daiviet@gmail.com | Địa chỉ: 67 CMT8, Q3, HCM
   - Trường THPT Nguyễn Du | MST: 0332109876 | ĐT: 0978901234 | Email: nguyendu@gmail.com | Địa chỉ: 12 Nguyễn Du, Q1, HCM

4. Tạo 5 nhà cung cấp (vào Contacts → Contacts → New, check Is Vendor):
   - Công ty Alu Miền Nam | ĐT: 0281234567 | Email: alumiennam@gmail.com
   - Nhà CC LED & Điện Quang | ĐT: 0282345678 | Email: ledquang@gmail.com
   - Xưởng Cơ Khí Tiến Đạt | ĐT: 0283456789 | Email: tiendat@gmail.com
   - Đội Thi Công Hoàng Nam | ĐT: 0284567890 | Email: hoangnam@gmail.com
   - Công ty Vận Chuyển & Xe Cẩu Minh Phát | ĐT: 0285678901 | Email: minhphat@gmail.com

5. Tạo 12 sản phẩm dịch vụ (vào Sales → Products → Products → New):
   - Khảo sát hiện trường | Loại: Service | Giá: 500000
   - Thiết kế biển | Loại: Service | Giá: 2000000
   - Gia công khung sắt | Loại: Service | Giá: 1500000
   - Ốp mặt Alu | Loại: Service | Giá: 3000000
   - Chữ nổi Inox | Loại: Service | Giá: 5000000
   - Hộp đèn LED | Loại: Service | Giá: 8000000
   - Thi công lắp đặt | Loại: Service | Giá: 2500000
   - Vận chuyển | Loại: Service | Giá: 1000000
   - Thuê xe cẩu/xe nâng | Loại: Service | Giá: 3500000
   - Tháo dỡ biển cũ | Loại: Service | Giá: 1500000
   - Bảo trì định kỳ | Loại: Service | Giá: 800000
   - Phát sinh thi công | Loại: Service | Giá: 0

6. Tạo 8 cơ hội CRM (vào CRM → Sales → My Pipeline → New):
   - Biển hiệu showroom Nguyễn Văn Linh | KH: Công ty TNHH Nội Thất Thủ Đức | Team: KD - Nguồn công ty | Doanh thu: 185000000 | Stage: Qualified
   - Biển LED An Nhiên Bình Thạnh | KH: Chuỗi Showroom An Nhiên | Team: KD - Nguồn công ty | Doanh thu: 143500000 | Stage: Proposition
   - Mặt dựng showroom Thủ Đức | KH: Công ty TNHH Nội Thất Thủ Đức | Team: KD - Tự khai thác | Doanh thu: 320000000 | Stage: Won
   - Biển quảng cáo siêu thị | KH: Siêu Thị Điện Máy Phú Nhuận | Team: KD - Tự khai thác | Doanh thu: 95000000 | Stage: New
   - Bảng hiệu nhà hàng | KH: Nhà Hàng Hải Sản Bình Dương | Team: KD - Nguồn công ty | Doanh thu: 75000000 | Stage: New
   - Biển công ty Đại Việt | KH: Công ty CP Quảng Cáo Đại Việt | Team: KD - Tự khai thác | Doanh thu: 250000000 | Stage: Qualified
   - Biển trường học | KH: Trường THPT Nguyễn Du | Team: KD - Nguồn công ty | Doanh thu: 45000000 | Stage: New
   - Hệ thống biển An Phú | KH: Công ty TNHH Thương Mại An Phú | Team: KD - Tự khai thác | Doanh thu: 520000000 | Stage: Proposition

7. Tạo 3 báo giá (vào Sales → Orders → Quotations → New):
   - BG001: KH Chuỗi Showroom An Nhiên | Sản phẩm: Gia công khung sắt x1 + Ốp mặt Alu x2 + Hộp đèn LED x3 + Thi công lắp đặt x1 + Vận chuyển x1
   - BG002: KH Công ty TNHH Nội Thất Thủ Đức | Sản phẩm: Thiết kế biển x1 + Chữ nổi Inox x5 + Ốp mặt Alu x4 + Thi công lắp đặt x1
   - BG003: KH Công ty TNHH Nội Thất Thủ Đức | Sản phẩm: Ốp mặt Alu x8 + Chữ nổi Inox x10 + Hộp đèn LED x6 + Thiết kế biển x1 + Thi công lắp đặt x2

8. Xác nhận báo giá BG002 và BG003 thành Sales Order

9. Tạo 3 Project (vào Project → Projects → New):
   - CT001 - Biển hiệu showroom Nguyễn Văn Linh | KH: Công ty TNHH Nội Thất Thủ Đức | Deadline: 30 ngày tới
   - CT002 - Biển LED An Nhiên Bình Thạnh | KH: Chuỗi Showroom An Nhiên | Deadline: 20 ngày tới
   - CT003 - Mặt dựng & bảng hiệu showroom Thủ Đức | KH: Công ty TNHH Nội Thất Thủ Đức | Deadline: 45 ngày tới

10. Mỗi Project tạo các Task theo thứ tự stage:
    - Xác nhận bản vẽ/kích thước
    - Chuẩn bị vật tư
    - Gia công khung
    - Gia công Alu/Mica/chữ/LED
    - QC kiểm tra chất lượng
    - Chuẩn bị thi công
    - Thi công
    - Nghiệm thu

Sau mỗi bước thông báo kết quả và tiếp tục bước tiếp theo.
Nếu gặp lỗi, chụp màn hình và báo cáo lỗi cụ thể.
""",

    "contacts": "Chỉ tạo contacts (khách hàng + nhà cung cấp)",
    "crm": "Chỉ tạo CRM opportunities",
    "products": "Chỉ tạo products/services",
    "quotations": "Chỉ tạo quotations và confirm",
    "projects": "Chỉ tạo projects và tasks",
}


async def run_agent(url: str, user: str, password: str, gemini_key: str, scenario: str = "full"):
    """Chạy agent tự động thao tác Odoo."""

    try:
        from browser_use import Agent
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError:
        print("Thiếu thư viện. Chạy: pip install browser-use langchain-google-genai playwright")
        print("Sau đó: playwright install chromium")
        return

    os.environ["GEMINI_API_KEY"] = gemini_key

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-exp",
        google_api_key=gemini_key,
        temperature=0.1,
    )

    task = DEMO_SCENARIOS.get(scenario, DEMO_SCENARIOS["full"])
    task = task.format(url=url, user=user, password=password)

    print(f"\n{'='*60}")
    print(f"Odoo Demo Agent — Kịch bản: {scenario}")
    print(f"URL: {url}")
    print(f"='*60}\n")

    agent = Agent(
        task=task,
        llm=llm,
        max_actions_per_step=10,
        browser_config={
            "headless": False,  # True = chạy ngầm, False = thấy browser
            "slow_mo": 500,     # ms giữa mỗi action (tăng nếu Odoo load chậm)
        }
    )

    result = await agent.run(max_steps=200)
    print(f"\n{'='*60}")
    print("KẾT QUẢ:")
    print(result)


def main():
    parser = argparse.ArgumentParser(description="Odoo Demo Agent — Tự động nhập data demo")
    parser.add_argument("--url", default="https://demo.bizapps.vn", help="URL Odoo")
    parser.add_argument("--user", default="admin", help="Username Odoo")
    parser.add_argument("--password", required=True, help="Password Odoo")
    parser.add_argument("--gemini-key", required=True, help="Gemini API key")
    parser.add_argument(
        "--scenario",
        default="full",
        choices=list(DEMO_SCENARIOS.keys()),
        help="Kịch bản chạy (mặc định: full)"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Chạy browser ngầm (không hiện UI)"
    )

    args = parser.parse_args()
    asyncio.run(run_agent(
        url=args.url,
        user=args.user,
        password=args.password,
        gemini_key=args.gemini_key,
        scenario=args.scenario,
    ))


if __name__ == "__main__":
    main()
