#!/usr/bin/env python3
"""
odoo-bootstrap: Trình khởi tạo môi trường phát triển Odoo tự động.
Chạy: python3 bootstrap.py
"""

import sys
import os

# Đảm bảo Python 3.10+
if sys.version_info < (3, 10):
    print("❌ Yêu cầu Python 3.10 trở lên.")
    sys.exit(1)

# Thêm thư mục gốc vào sys.path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT_DIR)

from core.orchestrator import Orchestrator


def main() -> None:
    orchestrator = Orchestrator()
    orchestrator.run()


if __name__ == "__main__":
    main()
