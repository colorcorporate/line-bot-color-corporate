import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

def _mask(s):
    return f"{len(s)} chars, endswith:{s[-4:]}" if s else "MISSING"

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
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=f"รับแล้ว: {event.message.text}")
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
