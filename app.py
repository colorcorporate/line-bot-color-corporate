import os, time
from flask import Flask, request, abort
import requests

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, ImageMessage, FileMessage

app = Flask(__name__)

# ===== ENV (ตั้งบน Render) =====
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET       = os.getenv("LINE_CHANNEL_SECRET")

# ปลายทางในบ้าน (ขั้นก่อนคุณตั้ง BEE_API_URL = https://.../save)
BEE_API_URL   = os.getenv("BEE_API_URL", "").strip()
BEE_API_TOKEN = os.getenv("BEE_API_TOKEN", "").strip()
# สร้าง URL สำหรับเก็บรูปอัตโนมัติจาก BEE_API_URL
BEE_IMAGE_URL = BEE_API_URL.replace("/save", "/save_image") if BEE_API_URL else ""

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

    # 1) ส่ง payload ไปเก็บ (jsonl) ที่ BeeStation
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
    return "OK"

# ====== ตัวช่วยส่งรูป/ไฟล์เข้า BeeStation ======
def _post_binary_to_bee(binary_iter, message_id: str, default_ext: str = ".bin", content_type: str = ""):
    if not BEE_IMAGE_URL:
        return
    # เดา ext จาก content-type แบบง่าย
    ext = default_ext
    ct = (content_type or "").lower()
    if "jpeg" in ct: ext = ".jpg"
    elif "png" in ct: ext = ".png"
    elif "gif" in ct: ext = ".gif"
    elif "pdf" in ct: ext = ".pdf"
    elif "zip" in ct: ext = ".zip"

    try:
        # line-bot-sdk ให้เป็น iterator → รวมเป็น bytes
        raw = b"".join(chunk for chunk in binary_iter.iter_content(chunk_size=1024))
        headers = {"Authorization": f"Bearer {BEE_API_TOKEN}"} if BEE_API_TOKEN else {}
        url = f"{BEE_IMAGE_URL}?mid={message_id}&ext={ext}"
        r = requests.post(url, headers=headers, data=raw, timeout=5)
        print("IMG FORWARDED:", r.status_code, url)
    except Exception as e:
        print("IMG FORWARD ERROR:", repr(e))

# ====== ไม่ตอบผู้ใช้ แต่ดึงสื่อเข้าบ้าน ======
@handler.add(MessageEvent, message=TextMessage)
def _handle_text(event):
    # เงียบ ไม่ reply
    return

@handler.add(MessageEvent, message=ImageMessage)
def _handle_image(event):
    # ดาวน์โหลดไฟล์ภาพจาก LINE แล้วส่งต่อเข้าบ้าน
    try:
        content = line_bot_api.get_message_content(event.message.id)
        _post_binary_to_bee(content, event.message.id, default_ext=".jpg", content_type=content.headers.get("Content-Type",""))
    except Exception as e:
        print("DOWNLOAD IMAGE ERROR:", repr(e))

@handler.add(MessageEvent, message=FileMessage)
def _handle_file(event):
    # ดาวน์โหลดไฟล์ (เช่น เอกสาร/สแกน) แล้วส่งต่อเข้าบ้าน
    try:
        content = line_bot_api.get_message_content(event.message.id)
        # เดา ext จาก content-type ถ้าไม่มีจะเป็น .bin
        _post_binary_to_bee(content, event.message.id, default_ext=".bin", content_type=content.headers.get("Content-Type",""))
    except Exception as e:
        print("DOWNLOAD FILE ERROR:", repr(e))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
