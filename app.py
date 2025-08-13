import os, json, uuid, datetime
from pathlib import Path
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError
from dotenv import load_dotenv

# โหลดไฟล์ ENV จากชื่อที่เรากำหนดเอง
load_dotenv("lineoa.env")

ACCESS_TOKEN = os.getenv("LINE_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
SAVE_ROOT = Path(os.getenv("SAVE_ROOT", r"E:\line_oa\inbox"))

app = Flask(__name__)
api = LineBotApi(ACCESS_TOKEN)
parser = WebhookParser(CHANNEL_SECRET)

def save_event(ev):
    day = datetime.datetime.now().strftime("%Y-%m-%d")
    eid = f"evt_{uuid.uuid4().hex[:8]}"
    outdir = SAVE_ROOT / day / eid
    outdir.mkdir(parents=True, exist_ok=True)

    # บันทึกข้อมูลดิบ
    with open(outdir / "message.json", "w", encoding="utf-8") as f:
        json.dump(ev.as_json_dict(), f, ensure_ascii=False, indent=2)

    # ถ้ามีไฟล์/รูป ให้โหลดมาเก็บ
    msg = getattr(ev, "message", None)
    if msg and getattr(msg, "id", None):
        try:
            content = api.get_message_content(msg.id)
            ext = ".bin"
            if getattr(msg, "type", "") == "image":
                ext = ".jpg"
            elif getattr(msg, "type", "") == "file":
                ext = f"_{getattr(msg,'fileName','file')}"
            with open(outdir / f"binary_{msg.id}{ext}", "wb") as bf:
                for chunk in content.iter_content():
                    bf.write(chunk)
        except Exception as e:
            with open(outdir / "error.txt", "a", encoding="utf-8") as ef:
                ef.write(str(e) + "\n")

@app.post("/webhook")
def webhook():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        abort(400)
    for ev in events:
        save_event(ev)
    return "OK"

@app.get("/health")
def health():
    return "OK"
