"""סוכן דוחות: דיווחים רשמיים ל-SEC (רשות ניירות הערך האמריקאית).
מקור רשמי וחינמי. הכללים שלהם: עד 10 בקשות בשנייה + זיהוי בכותרת. אנחנו הרבה מתחת.
"""
import datetime as dt, json, os
from . import net
import config

# סעיפים בדיווח מיידי (8-K): מה זה אומר ומשקל משוער לכיוון
ITEMS = {
    "1.01": ("נחתם הסכם מהותי", 0.3, True),
    "1.03": ("פשיטת רגל / כינוס", -3.0, True),
    "2.02": ("פורסמו תוצאות כספיות (דוח רבעוני)", 0.0, True),
    "2.05": ("תוכנית התייעלות / קיצוצים", -0.4, True),
    "2.06": ("מחיקת נכסים", -0.8, True),
    "3.01": ("אזהרת מחיקה מהמסחר", -2.0, True),
    "4.02": ("הדוחות הקודמים לא אמינים (תיקון דוחות)", -2.0, True),
    "5.02": ("שינוי בהנהלה הבכירה", -0.2, True),
    "7.01": ("הודעה למשקיעים", 0.0, False),
    "8.01": ("אירוע אחר שהחברה דיווחה", 0.0, False),
}

_cik_map = None
# מספרי זיהוי קבועים ב-SEC, כדי לא להוריד את כל הרשימה בכל הרצה
KNOWN_CIK = {"AAPL": 320193, "MSFT": 789019, "NVDA": 1045810, "AMZN": 1018724, "GOOGL": 1652044, "META": 1326801, "TSLA": 1318605, "AMD": 2488, "NFLX": 1065280, "JPM": 19617, "XOM": 2115436, "KO": 21344, "PLTR": 1321655, "INTC": 50863, "TEVA": 818686}


def cik_for(ticker):
    global _cik_map
    if ticker in KNOWN_CIK:
        return KNOWN_CIK[ticker]
    if _cik_map is None:
        path = os.path.join(config.DATA_DIR, "sec_tickers.json")
        fresh = os.path.exists(path) and (dt.datetime.now().timestamp() - os.path.getmtime(path)) < 7 * 86400
        if not fresh:
            txt = net.get("https://www.sec.gov/files/company_tickers.json", ua=config.SEC_USER_AGENT, min_gap=0.2)
            os.makedirs(config.DATA_DIR, exist_ok=True)
            open(path, "w").write(txt)
        _cik_map = {v["ticker"]: v["cik_str"] for v in json.load(open(path)).values()}
    return _cik_map.get(ticker.replace(".", "-"))


def analyze(ticker, days=3):
    out = {"ok": False, "score": 0.0, "signals": [], "alert": False, "data": {}, "filings": []}
    try:
        cik = cik_for(ticker)
        if not cik:
            out["error"] = "לא נמצאה ב-SEC (אולי חברה זרה)"
            return out
        d = net.get_json(f"https://data.sec.gov/submissions/CIK{cik:010d}.json", ua=config.SEC_USER_AGENT, min_gap=0.2)
    except Exception as e:
        out["error"] = str(e)[:200]
        return out
    r = d["filings"]["recent"]
    today = dt.date.today()
    insider7 = 0
    for i, form in enumerate(r["form"]):
        fdate = dt.date.fromisoformat(r["filingDate"][i])
        age = (today - fdate).days
        if age > 7:
            break
        acc = r["accessionNumber"][i].replace("-", "")
        link = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{r['primaryDocument'][i]}"
        if form == "4":
            insider7 += 1
            continue
        if age > days:
            continue
        if form in ("8-K", "6-K"):
            for item in [x.strip() for x in (r.get("items", [""] * (i + 1))[i] or "").split(",") if x.strip()]:
                if item in ITEMS:
                    text, w, alert = ITEMS[item]
                    out["signals"].append({"text": f"דיווח מיידי ({fdate:%d/%m}): {text}", "weight": w, "source": link})
                    out["alert"] |= alert
        elif form in ("10-Q", "10-K", "20-F"):
            kind = "דוח שנתי" if form in ("10-K", "20-F") else "דוח רבעוני"
            out["signals"].append({"text": f"הוגש {kind} מלא ({fdate:%d/%m})", "weight": 0.0, "source": link})
        elif form.startswith("SC 13D"):
            out["signals"].append({"text": f"משקיע גדול דיווח על החזקה של 5%+ עם כוונה להשפיע ({fdate:%d/%m})",
                                   "weight": 0.5, "source": link})
            out["alert"] = True
        out["filings"].append({"form": form, "date": fdate.isoformat(), "link": link})
    if insider7 >= 5:
        out["signals"].append({"text": f"{insider7} דיווחים של בעלי עניין (קניות/מכירות של מנהלים) בשבוע האחרון",
                               "weight": 0.0,
                               "source": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=4"})
    out["data"] = {"insider_7d": insider7}
    out["ok"] = True
    out["score"] = sum(s["weight"] for s in out["signals"])
    return out
