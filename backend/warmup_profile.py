import os
import sys

try:
    from cloakbrowser import launch_persistent_context
except ImportError:
    print("[-] CloakBrowser not found. Please install it first.")
    sys.exit(1)

def warmup():
    print("=" * 60)
    print("🚀 WARM-UP PROFILE TOOL 🚀")
    print("=" * 60)
    print("[*] Vui lòng sử dụng tool này để xây dựng Trust Score cho Profile.")
    print("[*] Khi trình duyệt mở lên, hãy làm các bước sau:")
    print("    1. Đăng nhập vào tài khoản Gmail (Google) của bạn.")
    print("    2. Lướt các trang web tin tức lớn hoặc YouTube một lát.")
    print("    3. Sau khi xong, ĐÓNG cửa sổ trình duyệt lại.")
    print("=" * 60)
    print("\n[*] Đang khởi động trình duyệt CloakBrowser với Persistent Context...")
    
    profile_dir = os.path.abspath("browser_profiles/default")
    os.makedirs(profile_dir, exist_ok=True)
    
    # Launch persistent context
    context = launch_persistent_context(
        user_data_dir=profile_dir,
        headless=False,
        humanize=True,
        viewport={"width": 1920, "height": 1080},
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--start-maximized"
        ]
    )
    
    page = context.pages[0] if context.pages else context.new_page()
    
    # Go to Google sign in
    print("[*] Đang điều hướng đến trang Đăng nhập Google...")
    try:
        page.goto("https://accounts.google.com", wait_until="domcontentloaded")
    except Exception as e:
        print(f"[-] Lỗi điều hướng: {e}")
        
    print("[+] Hoàn tất! Vui lòng đăng nhập trên cửa sổ trình duyệt.")
    print("[*] Script sẽ tự kết thúc khi bạn đóng cửa sổ trình duyệt.")
    
    try:
        page.wait_for_event("close", timeout=0)  # Wait forever until page closes
    except:
        pass
    
    print("\n[+] Đã đóng trình duyệt. Cookie và Trust Score đã được lưu vĩnh viễn!")
    print("[+] Bạn có thể quay lại chạy Dashboard/Crawler bình thường.")

if __name__ == "__main__":
    warmup()
