import os, time
from flask import Flask, request, abort
import requests

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent,
    TextMessage,
    ImageMessage,
    FileMessage,
)

app = Flask(__name__)

# ===== ENV บน Render =====
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET       = os.getenv("LINE_CHANNEL_SECRET")

# ปลายทางฝั่งบ้าน (ตั้งไว้เป็น https://.../save)
BEE_API_URL   = os.getenv("BEE_API_URL", "").strip()      # ex: https://xxx.trycloudflare.com/save
BEE_API_TOKEN = os.getenv("BEE_API_TOKEN", "").strip()
# สร้างปลายทางรับไฟล์อัตโนมัติจาก BEE_API_URL
BEE_IMAGE_URL = BEE_API_URL.replace("/save", "/save_image") if BEE_API_URL else ""

def _mask(s): return f"{len(s)} chars, endswith:{s[-4:]}" if s else "MISSING"
print("ENV CHECK | TOKEN:", _mask(CHANNEL_ACCESS_TOKEN), "| SECRET:", _mask(CHANNEL_SECRET))

if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET:
    raise RuntimeError("Missing LINE credentials in environment variables.")

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# ---------- Health ----------
@app.route("/", methods=["GET"])
def home():
    return "Bot is running"

# ---------- LINE Webhook ----------
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body_text = request.get_data(as_text=True)
    body_json = request.get_json(silent=True) or {}

    # 1) ส่ง payload ไปเก็บที่ BeeStation (jsonl วันละไฟล์)
    if BEE_API_URL:
        try:
            headers = {"Authorization": f"Bearer {BEE_API_TOKEN}"} if BEE_API_TOKEN else {}
            payload = {"received_at": int(time.time()), "line_webhook": body_json}
            requests.post(BEE_API_URL, json=payload, headers=headers, timeout=1.5)
        except Exception as e:
            print("FORWARD ERROR:", repr(e))  # log ไว้เฉย ๆ

    # 2) ตรวจลายเซ็น
    try:
        handler.handle(body_text, signature)
    except InvalidSignatureError:
        print("InvalidSignatureError: check LINE_CHANNEL_SECRET")
        abort(400)

    # ต้องตอบ 200 ให้ไว
    return "OK"

# ---------- ตัวช่วยส่งไฟล์ไบนารีเข้าบ้าน ----------
def _post_binary_to_bee(binary_resp, message_id: str, default_ext: str = ".bin"):
    """
    binary_resp: object ที่ได้จาก line_bot_api.get_message_content(message_id)
                 ใน SDK จะมี .iter_content() และ .content_type
    """
    if not BEE_IMAGE_URL:
        return

    # เดา ext จาก content_type
    content_type = getattr(binary_resp, "content_type", "application/octet-stream").lower()
    ext = default_ext
    if "jpeg" in content_type: ext = ".jpg"
    elif "png"  in content_type: ext = ".png"
    elif "gif"  in content_type: ext = ".gif"
    elif "pdf"  in content_type: ext = ".pdf"
    elif "zip"  in content_type: ext = ".zip"

    try:
        raw = b"".join(chunk for chunk in binary_resp.iter_content(chunk_size=1024))
        headers = {"Authorization": f"Bearer {BEE_API_TOKEN}"} if BEE_API_TOKEN else {}
        url = f"{BEE_IMAGE_URL}?mid={message_id}&ext={ext}"
        r = requests.post(url, headers=headers, data=raw, timeout=5)
        print("IMG FORWARDED:", r.status_code, url)
    except Exception as e:
        print("IMG FORWARD ERROR:", repr(e))

# ---------- ไม่ตอบผู้ใช้ (เงียบ) ----------
@handler.add(MessageEvent, message=TextMessage)
def _handle_text(event):
    return  # เงียบ

@handler.add(MessageEvent, message=ImageMessage)
def _handle_image(event):
    try:
        resp = line_bot_api.get_message_content(event.message.id)
        _post_binary_to_bee(resp, event.message.id, default_ext=".jpg")
    except Exception as e:
        print("DOWNLOAD IMAGE ERROR:", repr(e))

@handler.add(MessageEvent, message=FileMessage)
def _handle_file(event):
    try:
        resp = line_bot_api.get_message_content(event.message.id)
        _post_binary_to_bee(resp, event.message.id, default_ext=".bin")
    except Exception as e:
        print("DOWNLOAD FILE ERROR:", repr(e))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
