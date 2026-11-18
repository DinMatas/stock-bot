"""הופך את התחזיות להמלצה פשוטה: מה לעשות היום.
שני סלים: טווח קצר (ימים עד שבועות) וטווח ארוך (חודשים עד שנים).
זו המלצה אוטומטית לשימוש אישי, לא ייעוץ השקעות.
"""

TRIAL_MIN = 30  # עד שנבדקו לפחות 30 תחזיות, הבוט ב"תקופת ניסיון"


def conf_word(c):
    return "גבוה" if c >= 65 else "בינוני" if c >= 50 else "נמוך"


def _why(r, n=2):
    own = [s["text"] for s in r["signals"] if s["agent"] != "מאקרו" and s["weight"] != 0]
    info = [s["text"] for s in r["signals"] if s["agent"] != "מאקרו" and s["weight"] == 0]
    mac = [s["text"] for s in r["signals"] if s["agent"] == "מאקרו"]
    picks = (own + info + mac)[:n]
    return ". ".join(picks) if picks else "אין שום דבר מיוחד שקורה איתה"


def short_term(r):
    """קנייה / מכירה / להמתין, לכמה ימים עד שבועות."""
    d, c = r["direction"], r["confidence"]
    if not r["price"].get("price"):
        act = "hold"
    elif d == "up" and c >= 50:
        act = "buy"
    elif d == "down" and c >= 50:
        act = "sell"
    else:
        act = "hold"
    return {"action": act, "why": _why(r)}


def long_term(r):
    """האם כדאי להחזיק את המניה חודשים-שנים: איכות החברה (דוחות) + המגמה."""
    from agents.fundamentals import quality
    p = r["price"]
    s50, s200, price, rsi = p.get("sma50"), p.get("sma200"), p.get("price"), p.get("rsi")
    red_flag = any(s["agent"] == "דוחות" and s["weight"] <= -1 for s in r["signals"])
    q, qwhy = quality(r.get("fund"))
    qtxt = ", ".join(qwhy[:3])
    if red_flag:
        return {"action": "avoid", "q": q, "why": "יש דיווח רשמי מדאיג של החברה, עדיף להתרחק עד שיתברר"}
    if not (s50 and s200 and price):
        return {"action": "unknown", "q": q, "why": "אין מספיק היסטוריית מחירים"}
    up = price > s200 and s50 > s200
    down = price < s200 and s50 < s200
    if q is None:  # אין דוחות: רק לפי המגמה
        if up and not (rsi and rsi >= 70):
            return {"action": "buy", "q": 1, "why": "במגמת עלייה יציבה כבר חודשים"}
        return {"action": "avoid" if down else "wait", "q": q, "why": "במגמת ירידה כבר חודשים" if down else "בלי כיוון ברור כרגע"}
    pe = (r.get("fund") or {}).get("pe")
    if q >= 3 and pe and pe >= 60:
        return {"action": "wait", "q": q, "why": f"חברה שגדלה מהר ({qtxt}), אבל המניה יקרה מאוד. לחכות לירידה"}
    if q >= 3:
        if down:
            return {"action": "buy", "q": q, "why": f"חברה חזקה שהמחיר שלה ירד ({qtxt}). אפשר לקנות בהדרגה"}
        if rsi and rsi >= 70:
            return {"action": "wait", "q": q, "why": f"חברה חזקה ({qtxt}), אבל עלתה מהר לאחרונה. לחכות לירידה קטנה"}
        return {"action": "buy", "q": q, "why": f"חברה חזקה: {qtxt}"}
    if q <= 0:
        return {"action": "avoid", "q": q, "why": f"החברה חלשה כרגע: {qtxt}" if qtxt else "החברה חלשה כרגע"}
    return {"action": "wait", "q": q, "why": f"חברה בינונית: {qtxt}" if qtxt else "חברה בינונית"}


ACT_HE = {
    "buy": "קנה", "sell": "מכור", "hold": "חכה",
    "avoid": "לא עכשיו", "wait": "לחכות", "unknown": "אין מספיק מידע",
}


def plan(results):
    out = []
    for r in results:
        out.append({**r, "short": short_term(r), "long": long_term(r)})
    return out


def is_trial(stats):
    n = max((s["n"] for s in stats.values()), default=0)
    return n < TRIAL_MIN, n


def message(planned, macro, stats, title="מה עושים היום"):
    """הודעה קצרה לטלגרם: רק מה לקנות ומה למכור, ומתי. בלי סיכומים."""
    trial, n = is_trial(stats)
    L = [f"☀️ {title}", ""]
    buys = sorted([p for p in planned if p["short"]["action"] == "buy"], key=lambda p: -p["confidence"])
    sells = sorted([p for p in planned if p["short"]["action"] == "sell"], key=lambda p: -p["confidence"])
    longs = sorted([p for p in planned if p["long"]["action"] == "buy" and p not in buys and p not in sells], key=lambda p: -(p["long"].get("q") or 0))
    for p in buys:
        L.append(f"🟢 קנה {p['name']} · ביטחון {p['confidence']}%\nמתי: היום בפתיחת המסחר (16:30) · להחזיק: כמה ימים עד שבועיים\nלמה: {p['short']['why']}\n")
    for p in sells:
        L.append(f"🔴 מכור {p['name']} (אם יש לך) · ביטחון {p['confidence']}%\nמתי: היום בפתיחת המסחר\nלמה: {p['short']['why']}\n")
    if longs:
        L.append("🏦 לטווח ארוך (לקנות ולהחזיק חודשים-שנים):")
        for p in longs[:3]:
            L.append(f"• {p['name']}: {p['long']['why']}")
        L.append("")
    if not buys and not sells and not longs:
        L += ["⚪ היום לא עושים כלום. חכה.", ""]
    if trial:
        L.append(f"⚠️ תקופת ניסיון: עוד לא הוכחנו שהבוט צודק ({n} בדיקות). לא לשים כסף גדול.")
    L.append("לא ייעוץ השקעות, ההחלטה שלך.")
    return "\n".join(L)
