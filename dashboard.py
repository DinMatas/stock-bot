"""בונה את לוח הבקרה: דף אחד בעברית, נוח בטלפון ובמחשב."""
import datetime as dt, html, os
import config

DIR_HE = {"up": "עלייה", "down": "ירידה", "neutral": "ניטרלי"}
DIR_ICON = {"up": "▲", "down": "▼", "neutral": "●"}
AGENT_HE = {"מסחר": "מסחר", "חדשות": "חדשות", "דוחות": "דוחות", "מאקרו": "שוק"}

CSS = """
:root{
 /* פריסה: עמודה אחת בטלפון, כרטיסי התראה למעלה, טבלה מלאה למטה */
 --bg:#f3f5f4;--panel:#ffffff;--ink:#14201b;--muted:#5d6b65;--line:#dde3e0;
 --up:#0f7a4a;--up-bg:#e3f4ea;--down:#b42335;--down-bg:#fbe7ea;--flat:#6a6f73;--flat-bg:#eceeee;
 --accent:#1d5c8f;--warn:#a76200;--warn-bg:#fff3dc;
 --f-head:"Rubik","Heebo",system-ui,sans-serif;--f-body:"Heebo",system-ui,sans-serif;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
 --bg:#0f1513;--panel:#18211e;--ink:#e6eeea;--muted:#9aa9a2;--line:#2a3632;
 --up:#4fd08f;--up-bg:#123224;--down:#ff7d8c;--down-bg:#3a1a20;--flat:#a5abaf;--flat-bg:#242b29;
 --accent:#7ab8ea;--warn:#ffb94d;--warn-bg:#352812;color-scheme:dark}}
:root[data-theme="dark"]{
 --bg:#0f1513;--panel:#18211e;--ink:#e6eeea;--muted:#9aa9a2;--line:#2a3632;
 --up:#4fd08f;--up-bg:#123224;--down:#ff7d8c;--down-bg:#3a1a20;--flat:#a5abaf;--flat-bg:#242b29;
 --accent:#7ab8ea;--warn:#ffb94d;--warn-bg:#352812;color-scheme:dark}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);font-family:var(--f-body);font-size:15px;line-height:1.55;margin:0}
.wrap{max-width:980px;margin:0 auto;padding-block:20px 48px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));display:grid;gap:22px}
h1,h2,h3{font-family:var(--f-head);margin:0;text-wrap:balance}
h1{font-size:1.7rem;font-weight:700}
h2{font-size:1.15rem;font-weight:600}
.sub{color:var(--muted);font-size:.9rem}
a{color:var(--accent)}
.note{background:var(--warn-bg);color:var(--ink);border-radius:10px;padding:10px 14px;font-size:.85rem}
.market{display:flex;flex-wrap:wrap;gap:10px}
.chip{background:var(--panel);border:1px solid var(--line);border-radius:999px;padding:6px 12px;font-size:.88rem}
.chip b{font-variant-numeric:tabular-nums}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:12px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px;display:grid;gap:8px;min-width:0}
.card.up{border-inline-start:5px solid var(--up)}.card.down{border-inline-start:5px solid var(--down)}.card.neutral{border-inline-start:5px solid var(--flat)}
.top{display:flex;justify-content:space-between;align-items:baseline;gap:8px;flex-wrap:wrap}
.tk{font-family:var(--f-head);font-weight:700;font-size:1.1rem}
.nm{color:var(--muted);font-size:.85rem}
.pill{border-radius:999px;padding:2px 10px;font-weight:600;font-size:.85rem;white-space:nowrap}
.pill.up{background:var(--up-bg);color:var(--up)}.pill.down{background:var(--down-bg);color:var(--down)}.pill.neutral{background:var(--flat-bg);color:var(--flat)}
.meter{height:6px;background:var(--line);border-radius:3px;overflow:hidden}
.meter i{display:block;height:100%;background:var(--accent)}
.nums{display:flex;gap:14px;flex-wrap:wrap;font-size:.85rem;color:var(--muted);font-variant-numeric:tabular-nums}
.nums b{color:var(--ink)}
.pos{color:var(--up)}.neg{color:var(--down)}
ul.why{margin:0;padding-inline-start:18px;display:grid;gap:3px;font-size:.88rem}
.tag{font-size:.72rem;color:var(--muted);letter-spacing:.03em}
details{font-size:.85rem}
summary{cursor:pointer;color:var(--accent)}
.tbl{overflow-x:auto;background:var(--panel);border:1px solid var(--line);border-radius:12px}
table{border-collapse:collapse;width:100%;font-size:.88rem;font-variant-numeric:tabular-nums}
th,td{padding:8px 10px;text-align:start;border-bottom:1px solid var(--line);white-space:nowrap}
th{color:var(--muted);font-weight:500;font-size:.8rem}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.big{font-family:var(--f-head);font-size:1.6rem;font-weight:700;font-variant-numeric:tabular-nums}
.empty{color:var(--muted);font-size:.9rem}
.err{color:var(--warn);font-size:.8rem}
a:focus-visible,summary:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
"""


def _e(s):
    return html.escape(str(s))


def _pct(v):
    if v is None:
        return "—"
    cls = "pos" if v > 0 else "neg" if v < 0 else ""
    return f'<span class="{cls}">{v:+.1f}%</span>'


def _card(r):
    d, p = r["direction"], r["price"]
    reasons = "".join(
        f'<li>{_e(s["text"])} <a class="tag" href="{_e(s["source"])}" target="_blank" rel="noopener">{AGENT_HE.get(s["agent"], s["agent"])} ↗</a></li>'
        for s in r["signals"][:5]) or '<li class="empty">אין אותות מיוחדים</li>'
    heads = "".join(f'<li><a href="{_e(h["link"])}" target="_blank" rel="noopener">{_e(h["title"])}</a></li>'
                    for h in r["headlines"][:4])
    errs = "".join(f'<div class="err">לא הצלחתי למשוך {k}: {_e(v)[:80]}</div>' for k, v in r["errors"].items())
    price = f'<span>מחיר <b>${p["price"]:,}</b></span><span>היום {_pct(p.get("chg"))}</span><span>שבוע {_pct(p.get("chg5"))}</span>' if p.get("price") else ""
    return f"""<article class="card {d}">
 <div class="top"><div><span class="tk">{_e(r["ticker"])}</span> <span class="nm">{_e(r["name"])}</span></div>
 <span class="pill {d}">{DIR_ICON[d]} {DIR_HE[d]}</span></div>
 <div class="nums">{price}<span>ביטחון <b>{r["confidence"]}%</b></span></div>
 <div class="meter" title="רמת ביטחון"><i style="width:{r["confidence"]}%"></i></div>
 <ul class="why">{reasons}</ul>
 {f'<details><summary>כותרות אחרונות</summary><ul class="why">{heads}</ul></details>' if heads else ''}
 {errs}
</article>"""


def build(results, macro, stats, run_time):
    il = dt.datetime.fromisoformat(run_time).astimezone(dt.timezone(dt.timedelta(hours=2)))
    alerts = [r for r in results if r["alert"]]
    alerts.sort(key=lambda r: abs(r["score"]), reverse=True)
    m = macro.get("data", {})
    market = ""
    if m:
        market = (f'<div class="chip">S&amp;P 500 <b>{m["spx"]:,.0f}</b> · שבוע {_pct(m["spx_5d"])}</div>'
                  f'<div class="chip">מדד הפחד <b>{m["vix"]:.1f}</b></div>'
                  f'<div class="chip">ריבית 10 שנים <b>{m["t10"]:.2f}%</b></div>')
        market += "".join(f'<div class="chip">{_e(s["text"])}</div>' for s in macro["signals"][:2])
    else:
        market = f'<div class="err">אין נתוני שוק כרגע: {_e(macro.get("error", ""))[:80]}</div>'

    rows = ""
    for r in sorted(results, key=lambda r: r["score"], reverse=True):
        p = r["price"]
        rows += (f'<tr><td><b>{_e(r["ticker"])}</b> <span class="nm">{_e(r["name"])}</span></td>'
                 f'<td><span class="pill {r["direction"]}">{DIR_ICON[r["direction"]]} {DIR_HE[r["direction"]]}</span></td>'
                 f'<td>{r["confidence"]}%</td><td>{("$" + format(p["price"], ",")) if p.get("price") else "—"}</td>'
                 f'<td>{_pct(p.get("chg"))}</td><td>{p.get("vol_ratio", "—")}</td>'
                 f'<td>{r["news"].get("news_24h", "—")}</td><td>{"⚑" if r["alert"] else ""}</td></tr>')

    st = ""
    for h, s in stats.items():
        label = "אחרי יום מסחר" if h == 1 else f"אחרי {h} ימי מסחר"
        if s["n"]:
            st += (f'<div class="stat"><div class="sub">{label}</div><div class="big">{s["hit"]}%</div>'
                   f'<div class="sub">צדקה ב-{s["hit"]}% מתוך {s["n"]} תחזיות. '
                   f'רק עלייה/ירידה: {s["hit_dir"] if s["hit_dir"] is not None else "—"}% ({s["n_dir"]}). '
                   f'ביטחון 60%+: {s["hit_hi"] if s["hit_hi"] is not None else "—"}% ({s["n_hi"]})</div></div>')
        else:
            st += f'<div class="stat"><div class="sub">{label}</div><div class="big">—</div><div class="sub">עוד אין מספיק תחזיות שעבר עליהן הזמן</div></div>'

    cards = "".join(_card(r) for r in alerts) or '<p class="empty">כרגע אין משהו חריג. זה גם מידע.</p>'
    return f"""<title>לוח המניות של דין</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Heebo:wght@400;500;700&family=Rubik:wght@500;600;700&display=swap">
<style>{CSS}</style>
<div class="wrap" dir="rtl" lang="he">
 <header style="display:grid;gap:4px"><h1>לוח המניות</h1>
  <div class="sub">עודכן {il:%d/%m/%Y %H:%M} (שעון ישראל) · {len(results)} מניות במעקב · {len(alerts)} שווה לבדוק</div></header>
 <div class="note">⚠️ זה כלי עזר אישי, לא ייעוץ השקעות ולא המלצה לקנות או למכור. התחזיות אוטומטיות ויכולות לטעות. ההחלטה תמיד שלך.</div>
 <section style="display:grid;gap:10px"><h2>מצב השוק</h2><div class="market">{market}</div></section>
 <section style="display:grid;gap:10px"><h2>שווה לבדוק</h2><div class="cards">{cards}</div></section>
 <section style="display:grid;gap:10px"><h2>כל המניות</h2><div class="tbl"><table>
  <thead><tr><th>מניה</th><th>תרחיש</th><th>ביטחון</th><th>מחיר</th><th>היום</th><th>מחזור מול רגיל</th><th>כתבות 24ש׳</th><th>התראה</th></tr></thead>
  <tbody>{rows}</tbody></table></div></section>
 <section style="display:grid;gap:10px"><h2>כמה הבוט צודק?</h2><div class="stats">{st}</div>
  <div class="sub">"צדקה" = הכיוון שנחזה (עלייה / ירידה / ניטרלי) הוא מה שקרה. תזוזה קטנה מ-{config.NEUTRAL_BAND_PCT:g}% נחשבת ניטרלי. מטבע הוגן היה צודק בערך שליש מהפעמים.</div></section>
 <footer class="sub">מקורות: יאהו פיננס, גוגל חדשות, SEC EDGAR, FRED (הבנק הפדרלי של סנט לואיס). נתונים מתעדכנים בהשהיה.</footer>
</div>"""


def write(results, macro, stats, run_time):
    body = build(results, macro, stats, run_time)
    os.makedirs(config.OUT_DIR, exist_ok=True)
    full = f'<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">{body.split("<style>")[0]}<style>{CSS}</style></head><body>{body.split("</style>",1)[1]}</body></html>'
    open(os.path.join(config.OUT_DIR, "index.html"), "w").write(full)
    open(os.path.join(config.OUT_DIR, "artifact.html"), "w").write(body)
    return os.path.join(config.OUT_DIR, "index.html")
