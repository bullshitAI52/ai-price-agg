#!/usr/bin/env python3
"""Direct-grab Yunmao (catfk.com) shops via public goodsList API. Shop tokens from AIPrice sitemap."""
import re, json, urllib.request, urllib.parse, datetime, time

UA = {"User-Agent": "Mozilla/5.0 (compatible; MusePriceAgg/1.0)", "Referer": "https://catfk.com/"}
now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec="seconds")

sitemap = urllib.request.urlopen(urllib.request.Request("https://aiprice.club/sitemap-shops.xml", headers=UA), timeout=30).read().decode()
tokens = sorted(set(re.findall(r"market/shop/catfk-([a-zA-Z0-9_-]+)", sitemap)))
print("catfk tokens:", len(tokens))

def goods_page(token, page):
    data = urllib.parse.urlencode({"token": token, "keywords": "", "category_id": 0, "goods_type": "card", "current": page, "pageSize": 100}).encode()
    req = urllib.request.Request("https://catfk.com/shopApi/Shop/goodsList", data=data, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())

rows = []
for i, token in enumerate(tokens):
    try:
        first = goods_page(token, 1)
        total = first["data"]["total"]
        items = list(first["data"]["list"])
        page = 2
        while len(items) < total and page <= 20:
            d = goods_page(token, page)
            items.extend(d["data"]["list"]); page += 1
    except Exception as e:
        print("FAIL", token, e); continue
    for g in items:
        ext = g.get("extend") or {}
        user = g.get("user") or {}
        cat = (g.get("category") or {}).get("name") or ""
        rows.append({
            "title": g.get("name",""), "price": float(g.get("price") or 0),
            "market_price": (float(g["market_price"]) if g.get("market_price") else None),
            "stock": int(ext.get("stock_count", -1) if ext.get("stock_count") is not None else -1),
            "shop_name": user.get("nickname") or token, "platform": "云猫",
            "source": "直抓", "category": cat,
            "item_url": g.get("link") or f"https://catfk.com/item/{g.get('goods_key','')}",
            "shop_url": user.get("link") or f"https://catfk.com/shop/{token}",
            "shop_id": token, "goods_id": g.get("goods_key",""),
            "observed_at": now,
        })
    if (i+1) % 20 == 0: print(i+1, "shops, rows", len(rows))
json.dump(rows, open("raw/catfk.json","w"), ensure_ascii=False, indent=1)
print("TOTAL catfk direct rows:", len(rows), "shops with goods:", len(set(r['shop_id'] for r in rows)))
