"""סוכן רשתות חברתיות: StockTwits (רשת חברתית של משקיעים, חינמית, בלי מפתח).
כל משתמש שם יכול לתייג הודעה כ"שורי" (חושב שתעלה) או "דובי" (חושב שתרד).
בודקים: מה הרוב חושב ביממה האחרונה, והאם פתאום מדברים עליה הרבה יותר מהרגיל.
טוויטר/X לא נכלל: אין לו גישה חינמית חוקית.
"""
import datetime as dt
from . import net


def analyze(ticker):
    out = {"ok": False, "score": 0.0, "signals": [], "alert": False, "data": {}}
    try:
        d = net.get_json(f"https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json",
                         ua="Mozilla/5.0 (personal research bot)", min_gap=1.0, retries=1)
    except Exception as e:
        out["error"] = str(e)[:120]
        return out
    msgs = d.get("messages", [])
    now = dt.datetime.now(dt.timezone.utc)
    recent, bull, bear = 0, 0, 0
    for m in msgs:
        try:
            when = dt.datetime.fromisoformat(m["created_at"].replace("Z", "+00:00"))
        except Exception:
            continue
        if now - when > dt.timedelta(hours=24):
            continue
        recent += 1
        s = ((m.get("entities") or {}).get("sentiment") or {}).get("basic")
        if s == "Bullish":
            bull += 1
        elif s == "Bearish":
            bear += 1
    out["ok"] = True
    tagged = bull + bear
    out["data"] = {"posts_24h": recent, "bull": bull, "bear": bear}
    link = f"https://stocktwits.com/symbol/{ticker}"
    if tagged >= 8:
        ratio = bull / tagged
        if ratio >= 0.75:
            out["signals"].append({"text": f"ברשתות החברתיות רוב גדול חושב שהיא תעלה ({bull} מול {bear})",
                                   "weight": 0.6, "source": link})
        elif ratio <= 0.4:
            out["signals"].append({"text": f"ברשתות החברתיות הרבה חושבים שהיא תרד ({bear} מול {bull})",
                                   "weight": -0.6, "source": link})
    # השרת מחזיר עד 30 הודעות אחרונות. אם כולן מהשעות האחרונות = רעש חריג
    if len(msgs) >= 30 and recent >= 30:
        oldest = msgs[-1].get("created_at", "")  # הרשימה מסודרת מהחדש לישן
        try:
            span_h = (now - dt.datetime.fromisoformat(oldest.replace("Z", "+00:00"))).total_seconds() / 3600
        except Exception:
            span_h = 24
        if span_h <= 2:
            out["signals"].append({"text": "פתאום מדברים עליה המון ברשתות החברתיות", "weight": 0.0, "source": link})
            out["alert"] = True
    out["score"] = sum(s["weight"] for s in out["signals"])
    return out
