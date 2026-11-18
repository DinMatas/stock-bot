"""סוכן מאקרו: מצב השוק הכללי מנתוני הבנק הפדרלי של סנט לואיס (FRED), חינמי ורשמי.
נותן "מזג אוויר" לשוק כולו: פחד (VIX), כיוון ה-S&P 500, ריבית 10 שנים.
"""
import datetime as dt
from . import net

SERIES = {"VIXCLS": "מדד הפחד (VIX)", "SP500": "מדד S&P 500", "DGS10": "ריבית אג\"ח 10 שנים"}


def _series(sid):
    start = (dt.date.today() - dt.timedelta(days=60)).isoformat()
    txt = net.get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}&cosd={start}", ua=None, min_gap=0.5, timeout=40)
    vals = []
    for line in txt.strip().splitlines()[1:]:
        d, v = line.split(",")
        if v not in (".", ""):
            vals.append((d, float(v)))
    return vals


def analyze():
    out = {"ok": False, "score": 0.0, "signals": [], "data": {}}
    link = "https://fred.stlouisfed.org/series/"
    try:
        vix, spx, t10 = (_series(s) for s in SERIES)
    except Exception as e:
        out["error"] = str(e)[:200]
        return out
    out["ok"] = True
    v_now, v_prev = vix[-1][1], vix[-6][1] if len(vix) > 5 else vix[0][1]
    s_now, s_5 = spx[-1][1], spx[-6][1] if len(spx) > 5 else spx[0][1]
    s_20 = sum(x[1] for x in spx[-20:]) / min(20, len(spx))
    y_now, y_5 = t10[-1][1], t10[-6][1] if len(t10) > 5 else t10[0][1]
    spx5 = (s_now / s_5 - 1) * 100
    out["data"] = {"vix": v_now, "vix_date": vix[-1][0], "spx": s_now, "spx_5d": round(spx5, 2),
                   "spx_date": spx[-1][0], "t10": y_now, "t10_5d_bp": round((y_now - y_5) * 100)}

    def add(text, w, sid):
        out["signals"].append({"text": text, "weight": w, "source": link + sid})

    if v_now >= 30:
        add(f"פחד גבוה בשוק (VIX {v_now:.0f}), תנודות חדות צפויות", -0.6, "VIXCLS")
    elif v_now >= 20 and v_now > v_prev * 1.15:
        add(f"הפחד בשוק עולה (VIX {v_now:.0f})", -0.4, "VIXCLS")
    elif v_now < 15:
        add(f"שוק רגוע (VIX {v_now:.0f})", 0.2, "VIXCLS")
    if spx5 >= 2:
        add(f"השוק כולו עלה {spx5:.1f}% בשבוע האחרון", 0.4, "SP500")
    elif spx5 <= -2:
        add(f"השוק כולו ירד {spx5:.1f}% בשבוע האחרון", -0.4, "SP500")
    if s_now > s_20:
        add("ה-S&P 500 מעל הממוצע החודשי שלו (רוח גבית)", 0.2, "SP500")
    else:
        add("ה-S&P 500 מתחת לממוצע החודשי שלו (רוח נגדית)", -0.2, "SP500")
    bp = (y_now - y_5) * 100
    if bp >= 15:
        add(f"הריבית לטווח ארוך קפצה ב-{bp:.0f} נקודות בשבוע, לרוב לוחץ על מניות צמיחה", -0.3, "DGS10")
    elif bp <= -15:
        add(f"הריבית לטווח ארוך ירדה ב-{-bp:.0f} נקודות בשבוע, לרוב טוב למניות", 0.3, "DGS10")
    out["score"] = sum(s["weight"] for s in out["signals"])
    return out
