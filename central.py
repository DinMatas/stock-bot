"""הסוכן המרכזי: מאחד את כל הסוכנים לתרחיש אחד לכל מניה.
בגרסה הראשונה זה ניקוד שקוף לפי כללים (בלי בינה מלאכותית בתשלום),
כדי שאפשר יהיה לראות בדיוק למה כל תחזית יצאה כמו שיצאה.
"""
import config

MACRO_WEIGHT = 0.5  # השוק הכללי משפיע, אבל פחות מהמניה עצמה


def combine(ticker, name, price, news, filings, macro, social=None):
    parts = {"מסחר": price, "חדשות": news, "דוחות": filings}
    if social is not None:
        parts["רשתות"] = social
    signals = []
    for agent, res in parts.items():
        for s in res.get("signals", []):
            signals.append({**s, "agent": agent})
    for s in macro.get("signals", []):
        signals.append({**s, "agent": "מאקרו", "weight": round(s["weight"] * MACRO_WEIGHT, 2)})

    score = round(sum(s["weight"] for s in signals), 2)
    if score >= 1.0:
        direction = "up"
    elif score <= -1.0:
        direction = "down"
    else:
        direction = "neutral"

    # רמת ביטחון: כמה חזק הציון + כמה סוכנים מסכימים + כמה סוכנים בכלל עבדו
    agree = sum(1 for r in list(parts.values()) + [macro]
                if r.get("ok") and ((r["score"] > 0) if direction == "up" else (r["score"] < 0) if direction == "down" else abs(r["score"]) < 0.5))
    working = sum(1 for r in list(parts.values()) + [macro] if r.get("ok"))
    conf = 35 + min(abs(score), 4) * 8 + agree * 4
    if working < 4:
        conf -= (4 - working) * 10
    conf = int(max(20, min(80, conf)))  # לא מתיימרים ליותר מ-80%

    alert = any(r.get("alert") for r in parts.values()) or abs(score) >= config.ALERT_SCORE
    signals.sort(key=lambda s: abs(s["weight"]), reverse=True)
    return {
        "ticker": ticker, "name": name, "direction": direction, "confidence": conf, "score": score,
        "alert": alert, "signals": signals, "price": price.get("data", {}),
        "news": news.get("data", {}), "headlines": news.get("headlines", []),
        "errors": {k: v.get("error") for k, v in parts.items() if v.get("error")},
    }
