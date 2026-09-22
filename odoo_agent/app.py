"""
Odoo AI Agent — Web App
Chạy: python app.py
Mở: http://localhost:7799
"""

from __future__ import annotations
import asyncio
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from playwright.async_api import async_playwright
import google.generativeai as genai


HTML = """<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Odoo AI Agent</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,sans-serif;background:#f0f2f5;min-height:100vh;padding:24px}
.wrap{max-width:680px;margin:0 auto}
h1{font-size:22px;font-weight:700;margin-bottom:4px}
.sub{color:#666;font-size:14px;margin-bottom:24px}
.card{background:#fff;border-radius:12px;padding:24px;margin-bottom:16px;box-shadow:0 1px 4px rgba(0,0,0,.08)}
.card h2{font-size:15px;font-weight:600;margin-bottom:16px;color:#333}
label{display:block;font-size:13px;font-weight:500;color:#444;margin-bottom:5px;margin-top:12px}
label:first-of-type{margin-top:0}
input,textarea{width:100%;padding:9px 12px;border:1px solid #ddd;border-radius:8px;font-size:14px;outline:none;font-family:inherit}
input:focus,textarea:focus{border-color:#4F46E5}
textarea{min-height:140px;resize:vertical;line-height:1.5}
.row{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.btn{width:100%;padding:12px;background:#4F46E5;color:#fff;border:none;border-radius:8px;font-size:15px;font-weight:600;cursor:pointer;margin-top:16px;transition:background .2s}
.btn:hover{background:#4338CA}
.btn:disabled{background:#a5b4fc;cursor:not-allowed}
.log{background:#111;color:#4ade80;border-radius:8px;padding:16px;font-family:monospace;font-size:13px;min-height:120px;max-height:360px;overflow-y:auto;white-space:pre-wrap;display:none}
.status{display:none;align-items:center;gap:8px;font-size:13px;color:#555;margin-top:12px}
.dot{width:8px;height:8px;border-radius:50%;background:#4F46E5;animation:p 1s infinite}
@keyframes p{0%,100%{opacity:1}50%{opacity:.3}}
.tip{font-size:12px;color:#999;margin-top:4px}
.examples{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
.ex{font-size:12px;background:#EEF2FF;color:#4F46E5;padding:4px 10px;border-radius:20px;cursor:pointer;border:none}
.ex:hover{background:#E0E7FF}
</style>
</head>
<body>
<div class="wrap">
  <h1>🤖 Odoo AI Agent</h1>
  <p class="sub">Nhập mô tả — AI tự vào Odoo làm theo yêu cầu</p>

  <div class="card">
    <h2>Kết nối Odoo</h2>
    <label>URL Odoo</label>
    <input id="url" type="url" value="https://demo19.openerp.vn/" placeholder="https://your-odoo.com">
    <div class="row">
      <div>
        <label>Tài khoản</label>
        <input id="user" value="admin" placeholder="admin">
      </div>
      <div>
        <label>Mật khẩu</label>
        <input id="pass" type="password" value="admin" placeholder="admin">
      </div>
    </div>
    <label>Database (nếu có)</label>
    <input id="db" value="KETOANCE" placeholder="Để trống nếu 1 DB">
    <label>Gemini API Key</label>
    <input id="key" type="password" placeholder="AQ.Ab8... hoặc AIza...">
    <p class="tip">Lấy key miễn phí tại <a href="https://aistudio.google.com/apikey" target="_blank">aistudio.google.com/apikey</a></p>
  </div>

  <div class="card">
    <h2>Mô tả yêu cầu</h2>
    <label>Bạn muốn AI làm gì?</label>
    <textarea id="task" placeholder="Ví dụ: Tạo 5 khách hàng với tên, email, số điện thoại ngẫu nhiên cho ngành xây dựng..."></textarea>
    <div class="examples">
      <button class="ex" onclick="setTask('crm')">📊 Tạo CRM demo</button>
      <button class="ex" onclick="setTask('contacts')">👥 Tạo khách hàng</button>
      <button class="ex" onclick="setTask('products')">📦 Tạo sản phẩm</button>
      <button class="ex" onclick="setTask('avco')">📈 Demo Avg Costing</button>
      <button class="ex" onclick="setTask('quotation')">📄 Tạo báo giá</button>
      <button class="ex" onclick="setTask('inventory')">🏭 Nhập kho</button>
    </div>
    <button class="btn" id="btn" onclick="run()">▶ Chạy Agent</button>
    <div class="status" id="st"><div class="dot"></div><span id="stxt">Đang chạy...</span></div>
  </div>

  <div class="log" id="log"></div>
</div>

<script>
const TASKS = {
  crm: `Vào CRM → My Pipeline. Tạo 5 cơ hội bán hàng cho ngành biển quảng cáo:
1. Biển showroom Nguyễn Văn Linh - KH: Công ty Nội Thất ABC - Doanh thu: 185 triệu - Stage: Qualified
2. Biển LED An Nhiên Bình Thạnh - KH: Showroom An Nhiên - Doanh thu: 143 triệu - Stage: Proposition  
3. Mặt dựng showroom Thủ Đức - KH: Nội Thất Thủ Đức - Doanh thu: 320 triệu - Stage: Won
4. Biển siêu thị Phú Nhuận - KH: Siêu Thị XYZ - Doanh thu: 95 triệu - Stage: New
5. Bảng hiệu nhà hàng - KH: Nhà Hàng Bình Dương - Doanh thu: 75 triệu - Stage: New`,

  contacts: `Vào Contacts → New. Tạo 6 khách hàng cho ngành thi công biển quảng cáo:
1. Công ty TNHH Thương Mại An Phú | MST: 0312345678 | ĐT: 0901234567 | Email: anphu@gmail.com | Q7 HCM
2. Chuỗi Showroom An Nhiên | MST: 0387654321 | ĐT: 0923456789 | Email: annhien@gmail.com | Bình Thạnh HCM  
3. Công ty TNHH Nội Thất Thủ Đức | MST: 0376543210 | ĐT: 0934567890 | Email: thuduc@gmail.com | Thủ Đức
4. Siêu Thị Điện Máy Phú Nhuận | MST: 0365432109 | ĐT: 0945678901 | Email: phunhuan@gmail.com | Phú Nhuận
5. Nhà Hàng Hải Sản Bình Dương | MST: 0354321098 | ĐT: 0956789012 | Email: binhduong@gmail.com | Bình Dương
6. Công ty CP Quảng Cáo Đại Việt | MST: 0343210987 | ĐT: 0967890123 | Email: daiviet@gmail.com | Q3 HCM`,

  products: `Vào Sales → Products → Products. Tạo 8 sản phẩm dịch vụ cho công ty thi công biển quảng cáo:
1. Khảo sát hiện trường | Service | Giá: 500,000
2. Thiết kế biển | Service | Giá: 2,000,000
3. Gia công khung sắt | Service | Giá: 1,500,000
4. Ốp mặt Alu | Service | Giá: 3,000,000
5. Chữ nổi Inox | Service | Giá: 5,000,000
6. Hộp đèn LED | Service | Giá: 8,000,000
7. Thi công lắp đặt | Service | Giá: 2,500,000
8. Thuê xe cẩu/xe nâng | Service | Giá: 3,500,000`,

  avco: `Demo module sh_warehouse_avg Costing. Thực hiện theo thứ tự:
1. Vào Inventory → Configuration → Product Categories → tạo category "Vật tư AVCO" với Costing Method = Average Cost
2. Tạo sản phẩm "Sắt hộp 40x40" (Storable, category Vật tư AVCO)
3. Tạo PO lần 1: 100m giá 22,000/m → Confirm → Validate nhận hàng
4. Tạo PO lần 2: 50m giá 28,000/m → Confirm → Validate nhận hàng  
5. Vào sản phẩm xem giá vốn bình quân (phải là 24,000/m)
6. Vào Inventory → Reporting → xem báo cáo avg costing`,

  quotation: `Vào Sales → Orders → Quotations → New. Tạo 2 báo giá:
Báo giá 1 - KH: Chuỗi Showroom An Nhiên:
- Gia công khung sắt x1: 1,500,000
- Ốp mặt Alu x2: 6,000,000  
- Hộp đèn LED x3: 24,000,000
- Thi công lắp đặt x1: 2,500,000
→ Lưu (chưa confirm)

Báo giá 2 - KH: Công ty TNHH Nội Thất Thủ Đức:
- Thiết kế biển x1: 2,000,000
- Chữ nổi Inox x5: 25,000,000
- Ốp mặt Alu x4: 12,000,000
- Thi công lắp đặt x1: 2,500,000
→ Confirm thành Sales Order`,

  inventory: `Demo nhập kho vật tư:
1. Vào Inventory → Products → tạo 3 sản phẩm storable:
   - Sắt hộp 40x40 (đơn vị: m)
   - Tấm Alu 1220x2440 (đơn vị: tấm)
   - Module LED SMD 5050 (đơn vị: cái)
2. Vào Inventory → Operations → Physical Inventory
3. Nhập tồn kho ban đầu:
   - Sắt hộp 40x40: 800m
   - Tấm Alu: 120 tấm
   - Module LED: 2000 cái
4. Apply All để xác nhận tồn kho`
};

function setTask(key){ document.getElementById('task').value = TASKS[key]; }

function log(msg){
  const el = document.getElementById('log');
  el.style.display = 'block';
  el.textContent += msg + '\\n';
  el.scrollTop = el.scrollHeight;
}

async function run(){
  const url = document.getElementById('url').value.trim();
  const user = document.getElementById('user').value.trim();
  const pass = document.getElementById('pass').value.trim();
  const db = document.getElementById('db').value.trim();
  const key = document.getElementById('key').value.trim();
  const task = document.getElementById('task').value.trim();

  if(!url||!pass||!key||!task){alert('Vui lòng nhập đầy đủ thông tin');return;}

  const btn = document.getElementById('btn');
  btn.disabled = true; btn.textContent = '⏳ Đang chạy...';
  document.getElementById('st').style.display = 'flex';
  document.getElementById('log').textContent = '';
  log('[' + new Date().toLocaleTimeString() + '] Bắt đầu...');
  log('URL: ' + url);

  try {
    const resp = await fetch('/run', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({url,user,pass,db,key,task})
    });
    const reader = resp.body.getReader();
    const dec = new TextDecoder();
    while(true){
      const {done,value} = await reader.read();
      if(done) break;
      dec.decode(value).split('\\n').filter(l=>l).forEach(l=>log(l));
    }
    log('\\n✅ Hoàn tất!');
    document.getElementById('stxt').textContent = 'Hoàn tất!';
  } catch(e) {
    log('❌ ' + e.message);
    document.getElementById('stxt').textContent = 'Lỗi';
  }

  btn.disabled = false; btn.textContent = '▶ Chạy Agent';
}
</script>
</body>
</html>"""


async def run_agent(url, user, password, db, gemini_key, task_desc):
    """Chạy agent dùng Playwright + Gemini trực tiếp."""
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel("gemini-2.0-flash")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
        )
        page = await browser.new_page(viewport={"width": 1280, "height": 900})

        logs = []

        def emit(msg):
            logs.append(msg)

        # Đăng nhập
        emit(f"🌐 Mở {url}")
        await page.goto(url, timeout=30000)
        await page.wait_for_timeout(2000)

        # Chọn DB nếu có
        if db:
            try:
                db_input = page.locator(f'[name="db"], option[value="{db}"]').first
                if await db_input.is_visible():
                    await db_input.click()
                    await page.wait_for_timeout(1000)
            except:
                pass

        # Login
        try:
            await page.fill('[name="login"], #login', user)
            await page.fill('[name="password"], #password', password)
            await page.click('[type="submit"], .btn-primary')
            await page.wait_for_timeout(3000)
            emit("✅ Đăng nhập thành công")
        except Exception as e:
            emit(f"⚠️ Login: {e}")

        # Chụp màn hình để AI xem
        screenshot = await page.screenshot()

        # Gửi task cho Gemini
        emit("🤖 Gửi yêu cầu cho Gemini AI...")

        prompt = f"""Bạn là Odoo automation expert. 
Tôi đã đăng nhập vào Odoo tại {url}.
Hãy cho tôi danh sách các bước cụ thể để thực hiện yêu cầu sau:

YÊU CẦU: {task_desc}

Trả lời dạng JSON list các bước, mỗi bước có:
- action: goto/click/fill/select/wait
- target: CSS selector hoặc text
- value: giá trị cần nhập (nếu có)
- description: mô tả bước

Chỉ trả JSON, không giải thích thêm."""

        response = model.generate_content([
            {"mime_type": "image/png", "data": screenshot},
            prompt
        ])

        emit("📋 Kế hoạch thực hiện:")
        emit(response.text[:500] + "..." if len(response.text) > 500 else response.text)

        # Thực thi từng bước theo hướng dẫn của Gemini
        # Đây là bước cơ bản — parse JSON và thực hiện actions
        try:
            import json, re
            json_match = re.search(r'\[.*\]', response.text, re.DOTALL)
            if json_match:
                steps = json.loads(json_match.group())
                for i, step in enumerate(steps[:20]):
                    try:
                        desc = step.get('description', '')
                        action = step.get('action', '')
                        target = step.get('target', '')
                        value = step.get('value', '')

                        emit(f"  [{i+1}] {desc}")

                        if action == 'goto' and value:
                            await page.goto(value, timeout=15000)
                            await page.wait_for_timeout(1500)
                        elif action == 'click' and target:
                            await page.click(target, timeout=5000)
                            await page.wait_for_timeout(800)
                        elif action == 'fill' and target and value:
                            await page.fill(target, str(value), timeout=5000)
                            await page.wait_for_timeout(300)
                        elif action == 'wait':
                            await page.wait_for_timeout(2000)

                    except Exception as e:
                        emit(f"  ⚠️ Bước {i+1} lỗi: {str(e)[:80]}")
        except Exception as e:
            emit(f"⚠️ Parse lỗi: {e}")

        await browser.close()
        emit("🏁 Xong!")
        return logs


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML.encode())

    def do_POST(self):
        if self.path != "/run":
            self.send_response(404); self.end_headers(); return

        data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()

        def write(msg):
            b = (msg + "\n").encode()
            self.wfile.write(f"{len(b):x}\r\n".encode() + b + b"\r\n")
            self.wfile.flush()

        def run_sync():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                logs = loop.run_until_complete(run_agent(
                    data["url"], data["user"], data["pass"],
                    data.get("db", ""), data["key"], data["task"]
                ))
                for line in logs:
                    write(line)
            except Exception as e:
                write(f"❌ Lỗi: {e}")
            finally:
                loop.close()
                self.wfile.write(b"0\r\n\r\n")
                self.wfile.flush()

        t = threading.Thread(target=run_sync)
        t.start()
        t.join()


if __name__ == "__main__":
    port = 7799
    print(f"✅ Odoo AI Agent chạy tại: http://localhost:{port}")
    print("📂 Mở trình duyệt vào địa chỉ trên để sử dụng")
    print("Ctrl+C để dừng\n")
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
