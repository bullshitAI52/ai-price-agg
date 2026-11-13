#!/usr/bin/env python3
"""Collect AIPrice (aiprice.club) md category tables. CC BY 4.0 - attribution required."""
import re, json, time, urllib.request, datetime

UA = {"User-Agent": "Mozilla/5.0 (compatible; MusePriceAgg/1.0)"}
def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "ignore")

now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec="seconds")
index = fetch("https://aiprice.club/md/index.md")
open("raw/aiprice_index.md","w").write(index)
cats = []  # (category_name, slug, md_url)
for line in index.splitlines():
    m = re.match(r"\| ([^|]+) \| ¥?[\d.,]+ \| ([^|]+) \| ([^|]+) \| ([\d/]+) \| (\d+) \| (https://aiprice\.club/md/market/category/([a-z0-9-]+)\.md|—) \|", line.strip())
    if m and m.group(6).startswith("http"):
        cats.append((m.group(1).strip(), m.group(7), m.group(6)))
print("categories with md:", len(cats))

PLATFORM = {"ldxp": ("wzyp", "https://wzyp.cn/shop/{}"), "catfk": ("云猫", "https://catfk.com/shop/{}"),
            "16688": ("16688", "https://www.16688.com.cn/shop/{}")}
rows = []
for cat_name, slug, url in cats:
    try:
        md = fetch(url)
    except Exception as e:
        print("FAIL", slug, e); continue
    in_table = False
    for line in md.splitlines():
        line = line.strip()
        if line.startswith("## 有货最便宜"):
            in_table = True; continue
        if in_table:
            if line.startswith("## ") or line.startswith("官方订阅"):
                break
            m = re.match(r"\| ([^|]+) \| ([^|]+) \| ¥([\d.,]+) \| ([^|]*) \| ([^|]*) \| (\d+) \| (https://aiprice\.club/market/shop/([^\s|]+)) \|", line)
            if not m: continue
            shop_name, title, price, delivery, warranty, stock, shop_page, shop_slug = [g.strip() for g in m.groups()]
            # shop_slug = <prefix>-<shop_id...> ; prefix is up to first '-'
            if "-" in shop_slug:
                prefix, shop_id = shop_slug.split("-", 1)
            else:
                prefix, shop_id = shop_slug, shop_slug
            if prefix in PLATFORM:
                platform, tmpl = PLATFORM[prefix]
                shop_url = tmpl.format(shop_id)
            else:
                # self-hosted / other: slug like aicdks-com -> domain aicdks.com
                platform = "自建站"
                shop_url = shop_page
            cat = cat_name + (f"·{delivery}" if delivery and delivery != "—" else "")
            rows.append({
                "title": title, "price": float(price.replace(",","")), "market_price": None,
                "stock": int(stock), "shop_name": shop_name, "platform": platform,
                "source": "AI价网", "category": cat, "item_url": "",
                "shop_url": shop_url, "shop_id": shop_id, "goods_id": "",
                "observed_at": now, "aiprice_shop_page": shop_page,
            })
    print(slug, "cumulative", len(rows))
json.dump(rows, open("raw/aiprice.json","w"), ensure_ascii=False, indent=1)
print("TOTAL aiprice rows:", len(rows))
