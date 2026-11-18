"""סוכן מסחר/טכני: מחירים, מחזור מסחר, ממוצעים נעים, RSI.
מקור ראשי: יאהו פיננס (לא רשמי, לשימוש אישי). גיבוי: Tiingo עם מפתח חינמי.
"""
import datetime as dt
from . import net
import config


def _yahoo(ticker):
    d = net.get_json(f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1y&interval=1d")
    r = d["chart"]["result"][0]
    q = r["indicators"]["quote"][0]
    rows = []
    for t, c, v, o in zip(r["timestamp"], q["close"], q["volume"], q["open"]):
        if c is None or v is None:
            continue
        rows.append({"date": dt.datetime.utcfromtimestamp(t).date().isoformat(), "close": c, "open": o or c, "volume": v})
    return rows, f"https://finance.yahoo.com/quote/{ticker}"


def _tiingo(ticker):
    start = (dt.date.today() - dt.timedelta(days=380)).isoformat()
    d = net.get_json(f"https://api.tiingo.com/tiingo/daily/{ticker}/prices?startDate={start}&token={config.TIINGO_KEY}")
    rows = [{"date": x["date"][:10], "close": x["adjClose"], "open": x["adjOpen"], "volume": x["adjVolume"]} for x in d]
    return rows, f"https://www.tiingo.com/{ticker}/overview"


def history(ticker):
    errors = []
    for fn in ([_tiingo, _yahoo] if config.TIINGO_KEY else [_yahoo]):
        try:
            rows, link = fn(ticker)
            if len(rows) >= 30:
                return rows, link
        except Exception as e:
            errors.append(f"{fn.__name__}: {e}")
    raise RuntimeError("; ".join(errors) or "אין נתוני מחיר")


def _sma(vals, n):
    return sum(vals[-n:]) / n if len(vals) >= n else None


def _rsi(closes, n=14):
    if len(closes) <= n:
        return None
    gains = losses = 0.0
    for a, b in zip(closes[-n - 1:-1], closes[-n:]):
        ch = b - a
        gains += max(ch, 0)
        losses += max(-ch, 0)
    if losses == 0:
        return 100.0
    rs = gains / losses
    return 100 - 100 / (1 + rs)


def analyze(ticker):
    out = {"ok": False, "score": 0.0, "signals": [], "alert": False, "data": {}}
    try:
        rows, link = history(ticker)
    except Exception as e:
        out["error"] = str(e)[:200]
        return out
    closes = [r["close"] for r in rows]
    vols = [r["volume"] for r in rows]
    last, prev = rows[-1], rows[-2]
    chg = (last["close"] / prev["close"] - 1) * 100
    chg5 = (closes[-1] / closes[-6] - 1) * 100 if len(closes) > 5 else 0
    vol_avg = sum(vols[-21:-1]) / 20
    vol_ratio = last["volume"] / vol_avg if vol_avg else 1
    sma50, sma200 = _sma(closes, 50), _sma(closes, 200)
    rsi = _rsi(closes)
    hi52, lo52 = max(closes[-252:]), min(closes[-252:])
    gap = (last["open"] / prev["close"] - 1) * 100

    out["data"] = {"price": round(last["close"], 2), "date": last["date"], "chg": round(chg, 2), "chg5": round(chg5, 2),
                   "vol_ratio": round(vol_ratio, 2), "rsi": round(rsi, 1) if rsi else None,
                   "sma50": round(sma50, 2) if sma50 else None, "sma200": round(sma200, 2) if sma200 else None,
                   "chg1y": round((closes[-1] / closes[-252] - 1) * 100, 1) if len(closes) >= 252 else None}
    out["ok"] = True
    out["rows"] = rows
    sig = out["signals"]

    def add(text, w):
        sig.append({"text": text, "weight": w, "source": link})

    if abs(chg) >= config.BIG_MOVE_PCT:
        add(f"זזה {chg:+.1f}% ביום אחד, תזוזה חריגה", 0.5 if chg > 0 else -0.5)
        out["alert"] = True
    if vol_ratio >= config.VOLUME_SPIKE:
        # מחזור חריג מחזק את כיוון התזוזה
        w = 1.0 if chg > 0 else -1.0 if chg < 0 else 0
        add(f"קנו ומכרו אותה פי {vol_ratio:.1f} מהרגיל, משהו קורה", w)
        out["alert"] = True
    if abs(gap) >= 3:
        add(f"נפתחה בקפיצה של {gap:+.1f}% לעומת היום הקודם", 0.5 if gap > 0 else -0.5)
    if sma50 and sma200:
        if closes[-1] > sma50 > sma200:
            add("כבר כמה חודשים במגמת עלייה יציבה", 1.0)
        elif closes[-1] < sma50 < sma200:
            add("כבר כמה חודשים במגמת ירידה", -1.0)
    if rsi is not None:
        if rsi >= 75:
            add("עלתה מהר מדי לאחרונה, לפעמים אחרי זה מגיעה ירידה קטנה", -0.7)
        elif rsi <= 25:
            add("ירדה מהר מדי לאחרונה, לפעמים אחרי זה מגיעה קפיצה חזרה", 0.7)
    if closes[-1] >= hi52 * 0.99:
        add("במחיר הכי גבוה שלה בשנה האחרונה", 0.5)
    elif closes[-1] <= lo52 * 1.01:
        add("במחיר הכי נמוך שלה בשנה האחרונה", -0.5)
    out["score"] = sum(s["weight"] for s in sig)
    return out
