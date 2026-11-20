"""סורק כל השוק: עובר על כל ~7,000 המניות בארה"ב בבקשה אחת (לוח המניות של נאסד"ק, חינמי)
ובוחר את אלה שזזו הכי חריג. רק הן עוברות לבדיקה המעמיקה (חדשות, דוחות, רשתות).
מסננים החוצה מניות "זבל" שקל לתמרן: מחיר מתחת ל-3$, שווי חברה מתחת ל-300 מיליון$, מחזור נמוך.
"""
import re
from . import net

MIN_PRICE = 3.0
MIN_CAP = 300_000_000
MIN_VOLUME = 1_000_000
TOP = 10


def _num(s):
    n = re.sub(r"[^\d.\-]", "", str(s or ""))
    try:
        return float(n)
    except ValueError:
        return None


def movers(skip=()):
    d = net.get_json("https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=10000&download=true",
                     ua="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36",
                     timeout=40)
    rows = (d.get("data") or {}).get("rows") or []
    good = []
    for r in rows:
        sym = (r.get("symbol") or "").strip()
        if not sym or "^" in sym or "/" in sym or sym in skip:
            continue
        price, pct = _num(r.get("lastsale")), _num(r.get("pctchange"))
        cap, vol = _num(r.get("marketCap")), _num(r.get("volume"))
        if None in (price, pct, cap, vol) or price < MIN_PRICE or cap < MIN_CAP or vol < MIN_VOLUME:
            continue
        good.append({"ticker": sym, "name": (r.get("name") or sym)[:40], "pct": pct, "cap": cap})
    good.sort(key=lambda x: -abs(x["pct"]))
    return good[:TOP], len(rows)
