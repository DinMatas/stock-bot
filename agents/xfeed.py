"""סוכן טוויטר (X): קורא סיכום שנאסף מהכרום במק של דין (data/x_sentiment.json).
הקובץ מתעדכן כמה פעמים ביום ממשימה מתוזמנת. אם הוא ישן מ-8 שעות, מתעלמים ממנו.
מבנה: {"updated": "ISO", "tickers": {"AAPL": {"bull": 7, "bear": 2, "hot": false, "note": "..."}}}
"""
import datetime as dt, json, os
import config

PATH = os.path.join(config.DATA_DIR, "x_sentiment.json")


def analyze(ticker):
    out = {"ok": False, "score": 0.0, "signals": [], "alert": False, "data": {}}
    if not os.path.exists(PATH):
        out["error"] = "אין עדיין נתוני טוויטר"
        return out
    d = json.load(open(PATH))
    try:
        age = dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(d["updated"])
    except Exception:
        return out
    if age > dt.timedelta(hours=8):
        out["error"] = "נתוני טוויטר ישנים"
        return out
    t = d.get("tickers", {}).get(ticker)
    out["ok"] = True
    if not t:
        return out
    bull, bear = t.get("bull", 0), t.get("bear", 0)
    out["data"] = {"bull": bull, "bear": bear}
    link = f"https://x.com/search?q=%24{ticker}&f=live"
    note = t.get("note", "").strip()
    if bull + bear >= 6:
        r = bull / (bull + bear)
        if r >= 0.75:
            out["signals"].append({"text": "בטוויטר רוב גדול חושב שהיא תעלה" + (f": {note}" if note else ""), "weight": 0.6, "source": link})
        elif r <= 0.3:
            out["signals"].append({"text": "בטוויטר רוב גדול חושב שהיא תרד" + (f": {note}" if note else ""), "weight": -0.6, "source": link})
    if t.get("hot"):
        out["signals"].append({"text": "פתאום מדברים עליה המון בטוויטר" + (f": {note}" if note else ""), "weight": 0.0, "source": link})
        out["alert"] = True
    out["score"] = sum(s["weight"] for s in out["signals"])
    return out
