import os
import time
from ai_crawler_engine import SjcWebGiaCrawler

print("="*60)
print("TEST THỰC TẾ TRÊN TRANG WEB CÓ FORM ĐĂNG NHẬP")
print("="*60)

print("\n[!] Hãy nhập tài khoản bạn muốn Bot sử dụng (Hoặc ấn Enter để dùng tài khoản Demo).")
user = input("Username (Demo: student): ") or "Tieruz"
pwd = input("Password (Demo: trieuvo1123): ") or "trieuvo1123"

print("\n[!] Chọn trang web muốn test:")
print("1. Trang Demo Login (practicetestautomation.com) - Mặc định")
print("2. Trang GitHub (github.com/login) - Dùng để test MFA/OTP cực chuẩn")
print("3. Nhập URL trang web tự do")
choice = input("Lựa chọn (1/2/3) [Mặc định 1]: ") or "1"

if choice == "1":
    url = "https://practicetestautomation.com/practice-test-login/"
elif choice == "2":
    url = "https://github.com/login"
else:
    url = input("Nhập URL: ")

# Bơm tài khoản vào biến môi trường
os.environ["GOLD_SITE_USER"] = user
os.environ["GOLD_SITE_PASS"] = pwd

crawler = SjcWebGiaCrawler(use_ai_fallback=False)
crawler.target_url = url
crawler.credentials["username"] = user
crawler.credentials["password"] = pwd

print(f"\n[*] Bắt đầu phóng trình duyệt tới: {url}")
print("[*] HÃY NHÌN LÊN MÀN HÌNH ĐỂ XEM BOT TỰ ĐỘNG GÕ PHÍM NHÉ!")
time.sleep(2)

try:
    html = crawler._browser_fetch()
    if html:
        print("\n[+] Đã đăng nhập và tải trang xong! Độ dài HTML lấy được:", len(html))
        with open("github_test_output.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("[+] Đã lưu toàn bộ giao diện (HTML) của GitHub sau khi đăng nhập vào file 'github_test_output.html'")
        print("[+] Bạn có thể mở file này lên để thấy trang Dashboard cá nhân của bạn!")
    else:
        print("\n[-] Không lấy được HTML.")
except Exception as e:
    print(f"\n[!!!] Lỗi hoặc Yêu cầu Xử lý (HITL): {e}")

print("\n[+] Chạy thử nghiệm kết thúc.")
