import time
import os
from ai_crawler_engine import SjcWebGiaCrawler
import json

# Set test credentials
os.environ["GOLD_SITE_USER"] = "test_user"
os.environ["GOLD_SITE_PASS"] = "test_pass"

print("="*60)
print("TEST 1: KICH BAN DANG NHAP VA BI YEU CAU MFA/OTP")
print("="*60)

crawler1 = SjcWebGiaCrawler(use_ai_fallback=False)
crawler1.target_url = "http://127.0.0.1:8888/login"
crawler1.max_retries = 1 
try:
    result1 = crawler1._browser_fetch()
except Exception as e:
    result1 = str(e)

print("\n=> KET QUA TEST 1:")
print(json.dumps(result1, indent=2))

print("\n" + "="*60)
print("TEST 2: KICH BAN BI CHAN BOI CAPTCHA / CLOUDFLARE")
print("="*60)

crawler2 = SjcWebGiaCrawler(use_ai_fallback=False)
crawler2.target_url = "http://127.0.0.1:8888/captcha"
crawler2.max_retries = 1
try:
    result2 = crawler2._browser_fetch()
except Exception as e:
    result2 = str(e)

print("\n=> KET QUA TEST 2:")
print(json.dumps(result2, indent=2))
