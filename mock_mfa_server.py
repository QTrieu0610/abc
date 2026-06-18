from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
import uvicorn

app = FastAPI()

@app.get("/login", response_class=HTMLResponse)
async def get_login():
    return """
    <html>
        <body>
            <h2>Mock Target - Login</h2>
            <form method="post" action="/login">
                <input type="text" name="username" placeholder="Username" />
                <input type="password" name="password" placeholder="Password" />
                <button type="submit">Login</button>
            </form>
        </body>
    </html>
    """

@app.post("/login", response_class=HTMLResponse)
async def post_login(username: str = Form(...), password: str = Form(...)):
    # Trả về trang yêu cầu OTP (MFA)
    return """
    <html>
        <body>
            <h2>2-Step Verification</h2>
            <p>Please enter the OTP sent to your device.</p>
            <form method="post" action="/verify">
                <input type="text" name="otp" placeholder="Enter OTP" />
                <button type="submit">Verify</button>
            </form>
        </body>
    </html>
    """

@app.get("/captcha", response_class=HTMLResponse)
async def get_captcha():
    return """
    <html>
        <body>
            <h2>Security Check</h2>
            <p>Please verify you are a human. Cloudflare protection.</p>
            <div class="cloudflare"></div>
        </body>
    </html>
    """

if __name__ == "__main__":
    print("[+] Khởi chạy Mock Server tại http://127.0.0.1:8888")
    uvicorn.run(app, host="127.0.0.1", port=8888)
