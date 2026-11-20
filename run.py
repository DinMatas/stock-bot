"""הרצה אחת: כל הסוכנים -> סוכן מרכזי -> יומן תחזיות -> לוח בקרה.
הפעלה: python3 run.py
"""
import datetime as dt, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config, central, tracker, dashboard, advisor, notify, watch
from agents import prices, news, filings, macro, social, xfeed, fundamentals, ipo, scanner


def main():
    run_time = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    print("מאקרו...")
    mac = macro.analyze()
    results, hist = [], {}
    tickers = dict(config.WATCHLIST)
    scanned = {}
    try:
        picks, total = scanner.movers(skip=tickers)
        print(f"סורק: עבר על {total} מניות, נבחרו {len(picks)}")
        for x in picks:
            tickers[x["ticker"]] = x["name"]
            scanned[x["ticker"]] = x
    except Exception as e:
        print("הסורק נכשל:", e)
    for t, name in tickers.items():
        print(f"{t}...", flush=True)
        p = prices.analyze(t)
        if p.get("rows"):
            hist[t] = p.pop("rows")
        n = news.analyze(t, name)
        f = filings.analyze(t)
        s = social.analyze(t)
        r = central.combine(t, name, p, n, f, mac, s, xfeed.analyze(t))
        r["fund"] = fundamentals.analyze(t, r["price"].get("price"))
        if t in scanned:
            r["scan"] = scanned[t]
            r["signals"].insert(0, {"text": f"מניה פחות מוכרת שזזה חזק ({scanned[t]['pct']:+.0f}% ביום האחרון)", "weight": 0.0, "agent": "סורק", "source": ""})
        results.append(r)
    preds = tracker.log(results, run_time)
    preds = tracker.score_all(preds, hist)
    stats = tracker.stats(preds)
    os.makedirs(config.DATA_DIR, exist_ok=True)
    json.dump({"run_time": run_time, "macro": mac, "results": results}, open(os.path.join(config.DATA_DIR, "latest.json"), "w"),
              ensure_ascii=False, indent=1, default=str)
    planned = advisor.plan(results)
    path = dashboard.write(planned, mac, stats, run_time)
    send_messages(planned, mac, stats, run_time)
    send_weekly(preds, run_time)
    watch.check(results, hist)
    try:
        for txt in ipo.new_alerts():
            notify.send(txt + "\n\nלא ייעוץ השקעות.")
    except Exception as e:
        print("רדאר הנפקות נכשל:", e)
    alerts = [r["ticker"] for r in results if r["alert"]]
    print(f"מוכן: {path}\nשווה לבדוק: {', '.join(alerts) or 'אין'}")
    broken = {k for r in results for k in r["errors"]}
    if broken:
        print("סוכנים עם תקלות:", ", ".join(broken))


def send_messages(planned, mac, stats, run_time):
    """הודעת בוקר אחת ביום + התראה דחופה כשמשהו חדש וחזק קורה."""
    il_now = dt.datetime.fromisoformat(run_time) + dt.timedelta(hours=2)
    today = il_now.date().isoformat()
    sent = notify.load_sent()
    if sent.get("date") != today:
        sent = {"date": today, "daily": False, "alerts": []}
    try:
        if not sent["daily"]:
            if notify.send(advisor.message(planned, mac, stats, f"בוקר טוב דין, מה עושים היום ({il_now:%d/%m})")):
                sent["daily"] = True
        else:
            for p in planned:
                act = p["short"]["action"]
                key = f'{p["ticker"]}:{act}'
                strong = act in ("buy", "sell") and p["confidence"] >= 60
                if strong and key not in sent["alerts"]:
                    verb = "קנה" if act == "buy" else "מכור (או לא לקנות)"
                    txt = (f"🚨 עכשיו: {verb} {p['name']}\n"
                           f"ביטחון {advisor.conf_word(p['confidence'])} {p['confidence']}%\n"
                           f"למה: {p['short']['why']}\n\nהמלצה אוטומטית, לא ייעוץ השקעות.")
                    if notify.send(txt):
                        sent["alerts"].append(key)
    except Exception as e:
        print("שליחה לטלגרם נכשלה:", e)
    notify.save_sent(sent)


def send_weekly(preds, run_time):
    """פעם בשבוע, בהרצה האחרונה של יום שישי (אחרי סגירת המסחר): ציון דיוק."""
    now = dt.datetime.fromisoformat(run_time)
    il_now = now + dt.timedelta(hours=2)
    if il_now.weekday() != 4 or now.hour < 21:
        return
    path = os.path.join(config.DATA_DIR, "weekly.json")
    week = f"{il_now.isocalendar()[0]}-W{il_now.isocalendar()[1]}"
    done = json.load(open(path)) if os.path.exists(path) else {}
    if done.get("week") == week:
        return
    try:
        if notify.send(tracker.weekly_text(preds, il_now.date().isoformat())):
            json.dump({"week": week}, open(path, "w"))
    except Exception as e:
        print("שליחת הציון השבועי נכשלה:", e)


if __name__ == "__main__":
    main()
