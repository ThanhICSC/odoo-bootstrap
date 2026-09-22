# Odoo Demo Agent

AI Agent tự động thao tác Odoo theo kịch bản demo biển quảng cáo.
Dùng Browser Use + Gemini Pro — không cần API key Anthropic.

## Cài đặt

```bash
cd ~/odoo-agent
pip install browser-use playwright langchain-google-genai
playwright install chromium
```

## Lấy Gemini API Key

Vào https://aistudio.google.com/apikey → Create API Key → Copy

## Chạy

```bash
# Chạy toàn bộ kịch bản demo
python agent.py --url https://demo.bizapps.vn --user admin --password YOUR_PASS --gemini-key YOUR_KEY

# Chỉ tạo contacts
python agent.py --url https://demo.bizapps.vn --password xxx --gemini-key xxx --scenario contacts

# Chỉ tạo CRM
python agent.py --url https://demo.bizapps.vn --password xxx --gemini-key xxx --scenario crm

# Chạy ngầm (không hiện browser)
python agent.py --url https://demo.bizapps.vn --password xxx --gemini-key xxx --headless
```

## Các kịch bản

| Scenario | Mô tả |
|----------|-------|
| `full` | Toàn bộ: contacts, products, CRM, quotations, projects, tasks |
| `contacts` | Chỉ tạo 8 KH + 5 NCC |
| `products` | Chỉ tạo 12 sản phẩm dịch vụ |
| `crm` | Chỉ tạo 8 CRM opportunities |
| `quotations` | Chỉ tạo báo giá + confirm |
| `projects` | Chỉ tạo 3 projects + tasks |
