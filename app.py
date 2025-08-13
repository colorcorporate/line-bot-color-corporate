import os
from flask import Flask, request, abort

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# ====== อ่านค่า ENV (ตั้งบน Render) ======
# LINE_CHANNEL_ACCESS_TOKEN, LINE_CHANNEL_SECRET ต้องถูกต้องของ OA เดิม
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

def _mask(s: str | None) -> str:
    return f"{len(s)} chars, endswith:{s[-4:]}" if s else "MISSING"

print("ENV CHECK | TOKEN:", _mask(CHANNEL_ACCESS_TOKEN), "| SECRET:", _mask(CHANNEL_SECRET))

if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET:
    # ถ้าไม่มีค่า ให้หยุดทันที จะเห็นข้อความนี้ใน Logs
    raise RuntimeError("Missing LINE credentials in environment variables.")

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# ====== Health check ======
@app.route("/", methods=["GET"])
def home():
    return "Bot is running"

# ====== Webhook ที่ LINE จะเรียก ======
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    # DEBUG: แสดงข้อความสั้น ๆ ใน log (ไม่โชว์ข้อมูลส่วนตัว)
    print("Webhook body received (len):", len(body))

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        # ลายเซ็นไม่ถูกต้อง (มักเกิดจาก Channel Secret ไม่ตรง)
        print("InvalidSignatureError: check LINE_CHANNEL_SECRET")
        abort(400)

    # ต้องตอบ 200 OK ให้ไว เพื่อให้ Verify ผ่าน
    return "OK"

# ====== ตัวอย่างตอบกลับแบบ echo ======
@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    try:
        reply_text = f"รับแล้ว: {event.message.text}"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
    except Exception as e:
        # จับ error เวลา reply เพื่อดูใน Logs
        print("Reply error:", repr(e))

if __name__ == "__main__":
    # สำหรับรันในเครื่อง; บน Render จะใช้ gunicorn + $PORT
    app.run(host="0.0.0.0", port=10000)
