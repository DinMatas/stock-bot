"""סוכן דוחות לטווח ארוך: האם החברה עצמה טובה?
מקור: הדוחות השנתיים הרשמיים ב-SEC (חינמי, data.sec.gov/api/xbrl/companyfacts).
בודק: האם המכירות גדלות, האם יש רווח והאם הוא גדל, כמה חוב יש, וכמה "יקרה" המניה ביחס לרווח.
הנתונים משתנים רק פעם ברבעון, אז שומרים אותם בזיכרון (data/fundamentals.json) ומרעננים פעם ב-7 ימים.
"""
import datetime as dt, json, os
from . import net, filings
import config

CACHE = os.path.join(config.DATA_DIR, "fundamentals.json")
REV_TAGS = ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet",
            "RevenueFromContractWithCustomerIncludingAssessedTax"]


def _annual(facts, tags, unit="USD"):
    """מחזיר {שנה: ערך} מהדוחות השנתיים (10-K), לפי התגית הראשונה שיש בה נתונים עדכניים."""
    best = {}
    for tag in tags:
        node = facts.get("us-gaap", {}).get(tag)
        if not node:
            continue
        vals = {}
        for x in node.get("units", {}).get(unit, []):
            if x.get("form") not in ("10-K", "20-F") or x.get("fp") != "FY":
                continue
            s, e = x.get("start"), x.get("end")
            if s and e and not (330 <= (dt.date.fromisoformat(e) - dt.date.fromisoformat(s)).days <= 400):
                continue  # רק תקופה של שנה שלמה
            vals[e[:4]] = x["val"]  # לפי שנת סוף התקופה; דיווח מאוחר יותר דורס
        if vals and (not best or max(vals) > max(best)):
            best = vals
    return best


def _fetch(ticker):
    cik = filings.cik_for(ticker)
    if not cik:
        raise RuntimeError("לא נמצא מספר חברה ב-SEC")
    d = net.get_json(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{int(cik):010d}.json",
                     ua=config.SEC_USER_AGENT, min_gap=0.25, timeout=40)
    f = d.get("facts", {})
    rev = _annual(f, REV_TAGS)
    ni = _annual(f, ["NetIncomeLoss", "ProfitLoss"])
    eps = _annual(f, ["EarningsPerShareDiluted", "EarningsPerShareBasic"], "USD/shares")
    debt = _annual(f, ["LongTermDebtNoncurrent", "LongTermDebt"])
    eq = _annual(f, ["StockholdersEquity"])
    if len(rev) < 2 or not ni:
        raise RuntimeError("אין מספיק נתונים שנתיים")
    y = sorted(rev)[-1]
    py = str(int(y) - 1)
    out = {"year": y}
    if py in rev and rev[py]:
        out["rev_growth"] = round((rev[y] / rev[py] - 1) * 100, 1)
    if y in ni:
        out["profit"] = ni[y]
        out["margin"] = round(ni[y] / rev[y] * 100, 1) if rev[y] else None
        if py in ni and ni[py] > 0:
            out["profit_growth"] = round((ni[y] / ni[py] - 1) * 100, 1)
    if y in eps:
        out["eps"] = eps[y]
    if y in debt and y in eq and eq[y] > 0:
        out["debt_to_equity"] = round(debt[y] / eq[y], 2)
    return out


def analyze(ticker, price=None):
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    rec = cache.get(ticker)
    today = dt.date.today()
    if not rec or (today - dt.date.fromisoformat(rec["fetched"])).days >= 7:
        try:
            rec = {"fetched": today.isoformat(), **_fetch(ticker)}
            cache[ticker] = rec
            json.dump(cache, open(CACHE, "w"), ensure_ascii=False, indent=1)
        except Exception as e:
            if not rec:
                return {"ok": False, "error": str(e)[:120]}
    r = dict(rec)
    if price and r.get("eps") and r["eps"] > 0:
        r["pe"] = round(price / r["eps"], 1)
    r["ok"] = True
    return r


def quality(f):
    """ציון איכות החברה לטווח ארוך + הסבר פשוט. מחזיר (ציון, [סיבות])."""
    if not f or not f.get("ok"):
        return None, []
    s, why = 0, []
    g = f.get("rev_growth")
    if g is not None:
        if g >= 15:
            s += 2; why.append(f"המכירות גדלו {g:.0f}% בשנה")
        elif g >= 5:
            s += 1; why.append(f"המכירות גדלו {g:.0f}% בשנה")
        elif g < 0:
            s -= 1; why.append(f"המכירות ירדו {abs(g):.0f}% בשנה")
    p = f.get("profit")
    if p is not None:
        if p <= 0:
            s -= 2; why.append("החברה מפסידה כסף")
        else:
            s += 1
            pg = f.get("profit_growth")
            if pg is not None and pg >= 10:
                s += 1; why.append(f"הרווח גדל {pg:.0f}%")
            elif pg is not None and pg <= -20:
                s -= 1; why.append(f"הרווח ירד {abs(pg):.0f}%")
    pe = f.get("pe")
    if pe:
        if pe <= 25:
            s += 1; why.append(f"מחיר סביר (פי {pe:.0f} מהרווח השנתי)")
        elif pe >= 60:
            s -= 1; why.append(f"יקרה מאוד (פי {pe:.0f} מהרווח השנתי)")
    de = f.get("debt_to_equity")
    if de is not None and de >= 2:
        s -= 1; why.append("יש לה הרבה חובות")
    return s, why
