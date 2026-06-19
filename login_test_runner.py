import contextlib
import io
import os
import sys
from datetime import datetime
from typing import Callable, Dict, Optional


TARGETS = {
    "demo": {
        "label": "Demo Login",
        "url": "https://practicetestautomation.com/practice-test-login/",
    },
    "github": {
        "label": "GitHub Login",
        "url": "https://github.com/login",
    },
    "batdongsan": {
        "label": "Batdongsan Login",
        "url": "https://batdongsan.com.vn/nha-dat-ban",
    },
    "alonhadat": {
        "label": "AloNhaDat Login",
        "url": "https://alonhadat.com.vn/nha-dat/can-ban.html",
    },
}


def resolve_target(target_type: str, target_url: Optional[str] = None) -> Dict[str, str]:
    target_key = (target_type or "demo").lower()
    if target_key == "custom":
        url = (target_url or "").strip()
        if not (url.startswith("http://") or url.startswith("https://")):
            raise ValueError("Custom target URL must start with http:// or https://")
        return {"label": "Custom Login Target", "url": url}

    if target_key not in TARGETS:
        raise ValueError("Invalid target_type. Use demo, github, or custom.")

    return TARGETS[target_key]


def classify_signal(message: str) -> Optional[str]:
    value = (message or "").lower()
    if any(token in value for token in ["mfa", "otp", "two-factor", "2-step", "2 step"]):
        return "mfa_required"
    if any(token in value for token in ["captcha", "cloudflare", "verify you are a human", "security check"]):
        return "captcha_detected"
    if "access denied" in value or "403" in value:
        return "access_denied"
    if "timeout" in value:
        return "timeout"
    if "playwright" in value or "browser" in value:
        return "browser_event"
    return None


class LogCapture(io.TextIOBase):
    def __init__(
        self,
        emit: Callable[[str, str, Optional[str]], None],
        redactions: Dict[str, str],
        output_stream,
        error_stream,
    ):
        self.emit = emit
        self.redactions = redactions
        self.output_stream = output_stream
        self.error_stream = error_stream
        self.buffer = ""

    def writable(self):
        return True

    def write(self, text):
        self.buffer += str(text)
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            self._emit_line(line)
        return len(str(text))

    def flush(self):
        if self.buffer.strip():
            self._emit_line(self.buffer)
        self.buffer = ""

    def _emit_line(self, line: str):
        message = line.strip()
        if not message:
            return
        for secret, replacement in self.redactions.items():
            if secret:
                message = message.replace(secret, replacement)
        signal_type = classify_signal(message)
        level = "warning" if signal_type else "info"
        with contextlib.redirect_stdout(self.output_stream), contextlib.redirect_stderr(self.error_stream):
            self.emit(level, message, signal_type)


def run_login_test(
    *,
    job_id: str,
    target_type: str,
    target_url: Optional[str],
    username: str,
    password: str,
    profile_name: str,
    emit: Callable[[str, str, Optional[str]], None],
) -> Dict[str, object]:
    target = resolve_target(target_type, target_url)
    redactions = {
        password: "[password-hidden]",
    }

    emit("info", f"Starting login test for {target['label']} ({target['url']})", None)
    emit("info", "Authorized crawling only. Credentials are used only for this backend job.", None)

    from ai_crawler_engine import SjcWebGiaCrawler

    crawler = SjcWebGiaCrawler(use_ai_fallback=False, profile_name=profile_name or "default")
    crawler.target_url = target["url"]
    crawler.credentials["username"] = username
    crawler.credentials["password"] = password
    crawler.max_retries = 1

    output_file = None
    html = None
    capture = LogCapture(emit, redactions, sys.stdout, sys.stderr)

    with contextlib.redirect_stdout(capture), contextlib.redirect_stderr(capture):
        html = crawler._browser_fetch()
        capture.flush()

    html_length = len(html or "")
    if html:
        os.makedirs("login_test_outputs", exist_ok=True)
        output_file = os.path.join("login_test_outputs", f"{job_id}.html")
        with open(output_file, "w", encoding="utf-8") as handle:
            handle.write(html)
        emit("info", f"HTML captured successfully. Length: {html_length}", None)
        emit("info", f"Saved sanitized output file: {output_file}", None)
    else:
        emit("warning", "No HTML was captured from the login test.", "browser_error")

    return {
        "status": "completed" if html else "failed",
        "target_label": target["label"],
        "target_url": target["url"],
        "html_length": html_length,
        "output_file": output_file,
        "ended_at": datetime.now().isoformat(),
    }
