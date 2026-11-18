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
    """האם המניה מתאימה עכשיו להחזקה ארוכה."""
    p = r["price"]
    s50, s200, price, rsi = p.get("sma50"), p.get("sma200"), p.get("price"), p.get("rsi")
    red_flag = any(s["agent"] == "דוחות" and s["weight"] <= -1 for s in r["signals"])
    if not (s50 and s200 and price):
        return {"action": "unknown", "why": "אין מספיק היסטוריית מחירים"}
    y = p.get("chg1y")
    ytxt = f" (בשנה האחרונה {y:+.0f}%)" if y is not None else ""
    if red_flag:
        return {"action": "avoid", "why": "יש דיווח רשמי מדאיג של החברה, עדיף להתרחק עד שיתברר"}
    if price > s200 and s50 > s200:
        if rsi and rsi >= 70:
            return {"action": "wait", "why": f"חברה במגמת עלייה ארוכה{ytxt}, אבל עלתה מהר לאחרונה. עדיף לחכות לירידה קטנה ואז לקנות"}
        return {"action": "buy", "why": f"במגמת עלייה יציבה כבר חודשים{ytxt}"}
    if price < s200 and s50 < s200:
        return {"action": "avoid", "why": f"במגמת ירידה כבר חודשים{ytxt}. לא עכשיו"}
    return {"action": "wait", "why": f"בלי כיוון ברור כרגע{ytxt}"}


ACT_HE = {
    "buy": "לקנות", "sell": "למכור / לא לקנות", "hold": "להמתין",
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


def message(planned, macro, stats, title="מה לעשות היום"):
    """הודעת טקסט קצרה לטלגרם/מייל."""
    trial, n = is_trial(stats)
    L = [f"📊 {title}", ""]
    m = [s["text"] for s in macro.get("signals", [])[:2]]
    if m:
        L += ["🌡 השוק: " + ". ".join(m), ""]
    buys = sorted([p for p in planned if p["short"]["action"] == "buy"], key=lambda p: -p["confidence"])
    sells = sorted([p for p in planned if p["short"]["action"] == "sell"], key=lambda p: -p["confidence"])
    L.append("⚡ טווח קצר (ימים עד שבועות):")
    for p in buys:
        L.append(f"🟢 לקנות {p['name']} ({p['ticker']}), ביטחון {conf_word(p['confidence'])} {p['confidence']}%: {p['short']['why']}")
    for p in sells:
        L.append(f"🔴 למכור / לא לקנות {p['name']} ({p['ticker']}), ביטחון {conf_word(p['confidence'])} {p['confidence']}%: {p['short']['why']}")
    if not buys and not sells:
        L.append("⚪ אין היום הזדמנות ברורה. לא לגעת.")
    L += ["", "🏦 טווח ארוך (מניות שמתאימות עכשיו להחזקה):"]
    lb = [p for p in planned if p["long"]["action"] == "buy"]
    for p in lb:
        L.append(f"🟢 {p['name']} ({p['ticker']}): {p['long']['why']}")
    if not lb:
        L.append("⚪ אף מניה מהרשימה לא במצב טוב לקנייה ארוכה כרגע.")
    L.append("")
    if trial:
        L.append(f"⚠️ הבוט בתקופת ניסיון: נבדקו רק {n} תחזיות. עוד לא יודעים אם הוא צודק.")
    L.append("זו המלצה אוטומטית לשימוש אישי, לא ייעוץ השקעות. ההחלטה שלך.")
    L.append("הלוח המלא: https://dinmatas.github.io/stock-bot/")
    return "\n".join(L)
