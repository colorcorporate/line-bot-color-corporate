import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

# กันพลาด: ถ้าไม่มีค่า ให้ล้มพร้อมบอกสั้น ๆ ใน log (ไม่โชว์ความลับ)
def _mask(s): 
    return f"{len(s)} chars, endswith:{s[-4:]}" if s else "MISSING"

print("ENV CHECK | TOKEN:", _mask(CHANNEL_ACCESS_TOKEN), "| SECRET:", _mask(CHANNEL_SECRET))

if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET:
    raise RuntimeError("Missing LINE credentials in environment variables.")

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)
