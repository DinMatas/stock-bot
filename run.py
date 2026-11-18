"""הרצה אחת: כל הסוכנים -> סוכן מרכזי -> יומן תחזיות -> לוח בקרה.
הפעלה: python3 run.py
"""
import datetime as dt, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config, central, tracker, dashboard
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
    path = dashboard.write(results, mac, stats, run_time)
    alerts = [r["ticker"] for r in results if r["alert"]]
    print(f"מוכן: {path}\nשווה לבדוק: {', '.join(alerts) or 'אין'}")
    broken = {k for r in results for k in r["errors"]}
    if broken:
        print("סוכנים עם תקלות:", ", ".join(broken))


if __name__ == "__main__":
    main()
