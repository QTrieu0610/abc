import uuid

from login_test_runner import run_login_test


def emit(level, message, signal_type=None):
    prefix = {
        "error": "[!]",
        "warning": "[-]",
        "info": "[*]",
    }.get(level, "[*]")
    signal = f" ({signal_type})" if signal_type else ""
    print(f"{prefix}{signal} {message}")


def main():
    print("=" * 60)
    print("REAL LOGIN TEST")
    print("=" * 60)
    print("Credentials are used only for this run and are not logged.")

    username = input("Username (Demo: student): ") or "student"
    password = input("Password (Demo: Password123): ") or "Password123"

    print("\nChoose target:")
    print("1. Demo Login (practicetestautomation.com)")
    print("2. GitHub Login (github.com/login)")
    print("3. Custom URL")
    choice = input("Choice (1/2/3) [1]: ") or "1"

    target_type = "demo"
    target_url = None
    if choice == "2":
        target_type = "github"
    elif choice == "3":
        target_type = "custom"
        target_url = input("Custom URL: ")

    job_id = uuid.uuid4().hex
    try:
        result = run_login_test(
            job_id=job_id,
            target_type=target_type,
            target_url=target_url,
            username=username,
            password=password,
            profile_name="default",
            emit=emit,
        )
        print("\nResult:")
        for key, value in result.items():
            print(f"{key}: {value}")
    except Exception as exc:
        print(f"\n[!] Login test failed: {exc}")

    print("\nDone.")


if __name__ == "__main__":
    main()
