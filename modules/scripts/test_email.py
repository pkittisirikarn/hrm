"""
ทดสอบส่งอีเมลผ่าน EmailService
ใช้:
  (.venv) python -m modules.scripts.test_email --to someone@yourcompany.com --sub "Test" --body "Hello"
ถ้าไม่ใส่พารามิเตอร์ จะส่งหา EMAIL_FROM เอง (loopback)
"""

import argparse
import asyncio
from modules.common.email_service import EmailService

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--to", dest="to", help="อีเมลผู้รับ", default=None)
    parser.add_argument("--sub", dest="subject", help="หัวข้อ", default="HRM Test Email")
    parser.add_argument("--body", dest="body", help="ข้อความ", default="This is a test email from HRM.")
    args = parser.parse_args()

    svc = EmailService()
    to_addr = args.to or svc.settings.EMAIL_FROM  # ถ้าไม่ระบุ to ให้ยิงหา email ตัวเอง
    ok = await svc.send(to=[to_addr], subject=args.subject, body=args.body)
    print("SEND RESULT:", ok)

if __name__ == "__main__":
    asyncio.run(main())
