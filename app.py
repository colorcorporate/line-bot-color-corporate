import os, time
from flask import Flask, request, abort, jsonify
import requests

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage  # ไม่ใช้ reply

app = Flask(__name__)

# --- ตั้งค่าจาก ENV (ใส่บน Render) ---
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

# ปลายทางสำหรับเก็บข้อมูลภายใน (ถ้ามี)
BEE_API_URL   = os.getenv("BEE_API_URL", "").strip()     # เช่น http://192.168.1.50:5000/save
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

    # 1) ส่งต่อไปที่ BeeStation (ถ้าตั้งค่า BEE_API_URL ไว้)
    if BEE_API_URL:
        try:
            headers = {"Authorization": f"Bearer {BEE_API_TOKEN}"} if BEE_API_TOKEN else {}
            # ใส่เวลารับไว้ด้วย เผื่อจะใช้เรียงเหตุการณ์
            payload = {"received_at": int(time.time()), "line_webhook": body_json}
            requests.post(BEE_API_URL, json=payload, headers=headers, timeout=1.5)
        except Exception as e:
            # ไม่ให้ล้ม: แค่ log ไว้แล้วไปต่อ
            print("FORWARD ERROR:", repr(e))

    # 2) ตรวจลายเซ็น (เพื่อความถูกต้อง) — ไม่ตอบกลับผู้ใช้
    try:
        handler.handle(body_text, signature)
    except InvalidSignatureError:
        print("InvalidSignatureError: check LINE_CHANNEL_SECRET")
        abort(400)

    # 3) สำคัญ: ตอบกลับ LINE ทันทีด้วย 200 OK (ไม่ตอบหาผู้ใช้)
    return "OK"

# ทำ handler ว่าง ๆ เพื่อให้ parser ผ่าน (ไม่ตอบกลับ)
@handler.add(MessageEvent, message=TextMessage)
def _handle_text(event):
    return  # เงียบ

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
