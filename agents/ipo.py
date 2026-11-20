"""רדאר הנפקות: חברות גדולות שעומדות להתחיל להיסחר בבורסה האמריקאית.
מקור: לוח ההנפקות של נאסד"ק (חינמי, לא רשמי). מתריעים פעם אחת על כל הנפקה גדולה.
"""
import datetime as dt, json, os, re
from . import net
import config

STATE = os.path.join(config.DATA_DIR, "ipo_seen.json")
MIN_USD = 1_000_000_000  # רק הנפקות של מיליארד דולר ומעלה


def _money(s):
    n = re.sub(r"[^\d.]", "", s or "")
    return float(n) if n else 0


def upcoming():
    out = []
    today = dt.date.today()
    for m in {today.strftime("%Y-%m"), (today.replace(day=1) + dt.timedelta(days=32)).strftime("%Y-%m")}:
        d = net.get_json(f"https://api.nasdaq.com/api/ipo/calendar?date={m}",
                         ua="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36",
                         min_gap=1.0)
        rows = (((d.get("data") or {}).get("upcoming") or {}).get("upcomingTable") or {}).get("rows") or []
        for r in rows:
            usd = _money(r.get("dollarValueOfSharesOffered"))
            if usd >= MIN_USD:
                out.append({"ticker": r.get("proposedTickerSymbol"), "name": r.get("companyName"),
                            "date": r.get("expectedPriceDate"), "price": r.get("proposedSharePrice"), "usd": usd})
    return out


def new_alerts():
    """מחזיר טקסטים של התראות על הנפקות גדולות שעוד לא דיווחנו עליהן."""
    seen = json.load(open(STATE)) if os.path.exists(STATE) else []
    msgs = []
    for i in upcoming():
        key = f"{i['ticker']}:{i['date']}"
        if key in seen:
            continue
        seen.append(key)
        msgs.append(f"📅 הנפקה גדולה בדרך: {i['name']} ({i['ticker']})\n"
                    f"תאריך תמחור צפוי: {i['date']} · מחיר משוער למניה: {i['price']}$ · גיוס: {i['usd'] / 1e9:.1f} מיליארד$\n"
                    f"שים לב: ביום הראשון המחיר בדרך כלל קופץ מעל מחיר ההנפקה וגם מתנדנד חזק. "
                    f"אנשים רגילים קונים לפי מחיר הפתיחה בבורסה, לא לפי מחיר ההנפקה.")
    json.dump(seen, open(STATE, "w"), ensure_ascii=False, indent=1)
    return msgs
