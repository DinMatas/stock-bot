"""הרצה אחת: כל הסוכנים -> סוכן מרכזי -> יומן תחזיות -> לוח בקרה.
הפעלה: python3 run.py
"""
import datetime as dt, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config, central, tracker, dashboard, advisor, notify
from agents import prices, news, filings, macro


def main():
    run_time = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    print("מאקרו...")
    mac = macro.analyze()
    results, hist = [], {}
    for t, name in config.WATCHLIST.items():
        print(f"{t}...", flush=True)
        p = prices.analyze(t)
        if p.get("rows"):
            hist[t] = p.pop("rows")
        n = news.analyze(t, name)
        f = filings.analyze(t)
        results.append(central.combine(t, name, p, n, f, mac))
    preds = tracker.log(results, run_time)
    preds = tracker.score_all(preds, hist)
    stats = tracker.stats(preds)
    os.makedirs(config.DATA_DIR, exist_ok=True)
    json.dump({"run_time": run_time, "macro": mac, "results": results}, open(os.path.join(config.DATA_DIR, "latest.json"), "w"),
              ensure_ascii=False, indent=1, default=str)
    planned = advisor.plan(results)
    path = dashboard.write(planned, mac, stats, run_time)
    send_messages(planned, mac, stats, run_time)
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
            if notify.send(advisor.message(planned, mac, stats, f"מה לעשות היום ({il_now:%d/%m})")):
                sent["daily"] = True
        else:
            for p in planned:
                act = p["short"]["action"]
                key = f'{p["ticker"]}:{act}'
                strong = act in ("buy", "sell") and p["confidence"] >= 60
                if strong and key not in sent["alerts"]:
                    verb = "לקנות" if act == "buy" else "למכור / לא לקנות"
                    txt = (f"🚨 התראה: {verb} {p['name']} ({p['ticker']})\n"
                           f"ביטחון {advisor.conf_word(p['confidence'])} {p['confidence']}%\n"
                           f"למה: {p['short']['why']}\n\nהמלצה אוטומטית, לא ייעוץ השקעות.")
                    if notify.send(txt):
                        sent["alerts"].append(key)
    except Exception as e:
        print("שליחה לטלגרם נכשלה:", e)
    notify.save_sent(sent)


if __name__ == "__main__":
    main()
