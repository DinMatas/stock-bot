"""מעקב "תחתית": למניות שדין ביקש, מתריעים כשיש סימנים שהירידה נעצרה.
אף אחד לא יודע איפה התחתית האמיתית. אנחנו רק מזהים סימנים שהנפילה נרגעה.
כל התראה נשלחת פעם אחת בלבד (data/watch.json).
"""
import json, os, re
import config, notify
from agents.prices import _rsi

STATE = os.path.join(config.DATA_DIR, "watch.json")
CEO_RE = re.compile(r"\b(names?|named|appoints?|appointed|picks?|taps?)\b.*\bCEO\b|\bnew CEO\b|\bpermanent CEO\b", re.I)


def check(results, hist):
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    for t, since in config.WATCH_BOTTOM.items():
        rows = hist.get(t)
        r = next((x for x in results if x["ticker"] == t), None)
        if not rows or not r:
            continue
        name = r["name"]
        sent = state.setdefault(t, [])
        closes = [x["close"] for x in rows]
        last = closes[-1]
        recent = rows[-20:]
        low = min(recent, key=lambda x: x["close"])
        days_since_low = len(rows) - 1 - rows.index(low)
        sma10 = sum(closes[-10:]) / 10
        rsi = _rsi(closes)
        msgs = []
        # סימן 1: הירידה נעצרה - השפל לפני 3+ ימי מסחר, המחיר מעל ממוצע 10 ימים, ועלתה לפחות 3% ממנה
        key = f"stop:{low['date']}"
        if low["date"] >= since and days_since_low >= 3 and last > sma10 and last >= low["close"] * 1.03 and key not in sent:
            msgs.append((key, f"📍 {name}: נראה שהירידה נעצרה.\n"
                              f"הנקודה הכי נמוכה הייתה {low['close']:.2f}$ ב-{low['date'][8:10]}/{low['date'][5:7]}, "
                              f"ומאז כבר {days_since_low} ימי מסחר היא לא ירדה מתחתיה. עכשיו {last:.2f}$ "
                              f"({(last / low['close'] - 1) * 100:+.1f}% מהתחתית)."))
        # סימן 2: מינוי מנכ"ל קבוע
        for h in r.get("headlines", []):
            if CEO_RE.search(h["title"]):
                key = "ceo"
                if key not in sent:
                    msgs.append((key, f"📍 {name}: נראה שמינו מנכ\"ל קבוע. זה מה שהשוק חיכה לו.\n{h['title']}\n{h['link']}"))
                break
        for key, text in msgs:
            text += "\n\nזה סימן, לא הבטחה. אם קונים: בקטן ובהדרגה. לא ייעוץ השקעות."
            try:
                if notify.send(text):
                    sent.append(key)
            except Exception as e:
                print("התראת תחתית נכשלה:", e)
    json.dump(state, open(STATE, "w"), ensure_ascii=False, indent=1)
