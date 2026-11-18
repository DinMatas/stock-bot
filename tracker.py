"""יומן תחזיות ובדיקת דיוק.
כל תחזית נשמרת עם המחיר באותו רגע. אחרי יום מסחר אחד ואחרי 5 ימים
בודקים מה קרה בפועל ומסמנים: צדק / טעה.
"""
import json, os
import config
from agents import prices

PATH = os.path.join(config.DATA_DIR, "predictions.json")


def load():
    return json.load(open(PATH)) if os.path.exists(PATH) else []


def save(preds):
    os.makedirs(config.DATA_DIR, exist_ok=True)
    tmp = PATH + ".tmp"
    json.dump(preds, open(tmp, "w"), ensure_ascii=False, indent=1)
    os.replace(tmp, PATH)


def log(results, run_time):
    """תחזית אחת לכל מניה לכל יום מסחר. הרצה חוזרת באותו יום מעדכנת אותה."""
    preds = load()
    idx = {(p["ticker"], p["price_date"]): i for i, p in enumerate(preds)}
    for r in results:
        pd = r["price"]
        if not pd.get("price"):
            continue  # בלי מחיר אי אפשר לבדוק אחר כך
        rec = {"ticker": r["ticker"], "price_date": pd["date"], "made_at": run_time, "direction": r["direction"],
               "confidence": r["confidence"], "score": r["score"], "price": pd["price"],
               "reasons": [s["text"] for s in r["signals"][:3]], "results": {}}
        key = (r["ticker"], pd["date"])
        if key in idx:
            rec["results"] = preds[idx[key]].get("results", {})
            preds[idx[key]] = rec
        else:
            preds.append(rec)
    save(preds)
    return preds


def score_all(preds, history_cache):
    """ממלא תוצאות לתחזיות שכבר עבר מספיק זמן מאז שנעשו."""
    for p in preds:
        for h in config.HORIZONS:
            if str(h) in p["results"]:
                continue
            rows = history_cache.get(p["ticker"])
            if rows is None:
                try:
                    rows, _ = prices.history(p["ticker"])
                except Exception:
                    rows = []
                history_cache[p["ticker"]] = rows
            dates = [r["date"] for r in rows]
            if p["price_date"] not in dates:
                continue
            i = dates.index(p["price_date"])
            if i + h >= len(rows):
                continue
            move = (rows[i + h]["close"] / p["price"] - 1) * 100
            actual = "up" if move > config.NEUTRAL_BAND_PCT else "down" if move < -config.NEUTRAL_BAND_PCT else "neutral"
            p["results"][str(h)] = {"move": round(move, 2), "actual": actual, "hit": actual == p["direction"]}
    save(preds)
    return preds


def stats(preds):
    out = {}
    for h in config.HORIZONS:
        done = [p for p in preds if str(h) in p["results"]]
        directional = [p for p in done if p["direction"] != "neutral"]
        hi = [p for p in directional if p["confidence"] >= 60]
        rate = lambda xs: round(100 * sum(p["results"][str(h)]["hit"] for p in xs) / len(xs)) if xs else None
        out[h] = {"n": len(done), "hit": rate(done), "n_dir": len(directional), "hit_dir": rate(directional),
                  "n_hi": len(hi), "hit_hi": rate(hi)}
    return out
