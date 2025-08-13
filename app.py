import os, time
from flask import Flask, request, abort
import requests

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage  # เงียบ ไม่ตอบกลับ

app = Flask(__name__)

# ===== ENV จาก Render =====
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET       = os.getenv("LINE_CHANNEL_SECRET")

# ปลายทาง (ฝั่งบ้าน/ร้าน) ถ้าตั้งค่าไว้ จะส่งต่อทั้งก้อน
BEE_API_URL   = os.getenv("BEE_API_URL", "").strip()     # เช่น https://xxxx.trycloudflare.com/save
BEE_API_TOKEN = os.getenv("BEE_API_TOKEN", "").strip()

def _mask(s): return f"{len(s)} chars, endswith:{s[-4:]}" if s else "MISSING"
print("ENV CHECK | TOKEN:", _mask(CHANNEL_ACCESS_TOKEN), "| SECRET:", _mask(CHANNEL_SECRET))

if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET:
    raise RuntimeError("Missing LINE credentials in environment variables.")

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

@app.route("/", methods=["GET"])
def home():
    return "Bot is running"

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body_text = request.get_data(as_text=True)
    body_json = request.get_json(silent=True) or {}

    # ส่งต่อเข้าบ้าน (ถ้ากำหนด BEE_API_URL)
    if BEE_API_URL:
        try:
            headers = {"Authorization": f"Bearer {BEE_API_TOKEN}"} if BEE_API_TOKEN else {}
            payload = {"received_at": int(time.time()), "line_webhook": body_json}
            requests.post(BEE_API_URL, json=payload, headers=headers, timeout=1.5)
        except Exception as e:
            print("FORWARD ERROR:", repr(e))  # log แต่ไม่ให้ล้ม

    # ตรวจลายเซ็นและจบด้วย 200 OK (ไม่ตอบผู้ใช้)
    try:
        handler.handle(body_text, signature)
    except InvalidSignatureError:
        print("InvalidSignatureError: check LINE_CHANNEL_SECRET")
        abort(400)
    return "OK"

# Handler ว่าง ๆ เพื่อให้ parser ผ่าน (เราไม่ reply)
@handler.add(MessageEvent, message=TextMessage)
def _handle_text(event):
    return

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
