"""שליחת הודעות לטלגרם.
צריך סוד TELEGRAM_TOKEN בגיטהאב. את מספר הצ'אט הבוט מוצא לבד,
אחרי שדין שולח לבוט /start (נשמר ב-data/telegram_chat.json).
"""
import json, os, urllib.request, urllib.parse
import config

TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_FILE = os.path.join(config.DATA_DIR, "telegram_chat.json")
SENT_FILE = os.path.join(config.DATA_DIR, "sent.json")


def _api(method, **params):
    data = urllib.parse.urlencode(params).encode()
    with urllib.request.urlopen(f"https://api.telegram.org/bot{TOKEN}/{method}", data=data, timeout=20) as r:
        return json.loads(r.read())


def chat_id():
    cid = os.environ.get("TELEGRAM_CHAT_ID", "")
    if cid:
        return cid
    if os.path.exists(CHAT_FILE):
        return json.load(open(CHAT_FILE))["chat_id"]
    upd = _api("getUpdates").get("result", [])
    me = _api("getMe").get("result", {})
    print(f"בוט: @{me.get('username')} · עדכונים שהתקבלו: {len(upd)} · סוגים: {[list(u.keys())[1:] for u in upd][:5]}")
    chats = []
    for u in upd:
        for k in ("message", "edited_message", "my_chat_member"):
            if k in u and u[k]["chat"]["type"] == "private":
                chats.append(u[k]["chat"]["id"])
    if not chats:
        return None
    json.dump({"chat_id": chats[-1]}, open(CHAT_FILE, "w"))
    return chats[-1]


def send(text):
    if not TOKEN:
        print("אין TELEGRAM_TOKEN, לא נשלחה הודעה")
        return False
    cid = chat_id()
    if not cid:
        print("עוד לא שלחו /start לבוט, לא יודע לאן לשלוח")
        return False
    for i in range(0, len(text), 3800):  # מגבלת אורך של טלגרם
        _api("sendMessage", chat_id=cid, text=text[i:i + 3800], disable_web_page_preview="true")
    return True


def load_sent():
    return json.load(open(SENT_FILE)) if os.path.exists(SENT_FILE) else {}


def save_sent(s):
    json.dump(s, open(SENT_FILE, "w"), ensure_ascii=False, indent=1)
