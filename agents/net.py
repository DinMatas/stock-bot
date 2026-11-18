"""עזר לשליפת נתונים מהרשת, עם השהיה מנומסת וזיכרון מטמון קצר."""
import json, time, urllib.request, urllib.error

_last_call = {}


def get(url, ua="MatasStockWatch personal-research", min_gap=0.25, timeout=20, retries=2):
    host = url.split("/")[2]
    for attempt in range(retries + 1):
        gap = time.time() - _last_call.get(host, 0)
        if gap < min_gap:
            time.sleep(min_gap - gap)
        _last_call[host] = time.time()
        headers = {"Accept-Encoding": "identity"}
        if ua:
            headers["User-Agent"] = ua
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < retries:
                time.sleep(2 * (attempt + 1))
                continue
            raise
        except urllib.error.URLError:
            if attempt < retries:
                time.sleep(2)
                continue
            raise


def get_json(url, **kw):
    return json.loads(get(url, **kw))
