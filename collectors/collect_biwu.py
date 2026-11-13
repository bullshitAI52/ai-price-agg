#!/usr/bin/env python3
"""Collect BiWu.Ai standard product pages (quote tables). Attribution: BiWu.Ai."""
import re, json, urllib.request, datetime, html as H

UA = {"User-Agent": "Mozilla/5.0 (compatible; MusePriceAgg/1.0)"}
now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec="seconds")

sitemap = urllib.request.urlopen(urllib.request.Request("https://biwu.ai/sitemap.xml", headers=UA), timeout=30).read().decode()
slugs = sorted(set(re.findall(r"https://biwu\.ai/products/([a-z0-9-]+)", sitemap)))
print("biwu products:", len(slugs))

PLATFORM_MAP = {"链动小铺": "wzyp", "云猫寄售": "云猫", "云猫": "云猫", "16688": "16688", "独角数卡": "独角数卡", "独角数卡（Dujiao）": "独角数卡"}
def clean_url(u):
    u = H.unescape(u)
    return u.split("?")[0]

rows = []
for slug in slugs:
    url = f"https://biwu.ai/products/{slug}"
    try:
        page = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read().decode("utf-8","ignore")
    except Exception as e:
        print("FAIL", slug, e); continue
    tm = re.search(r"<title>([^<]+)</title>", page)
    title_tag = tm.group(1) if tm else slug
    cat_name = re.split(r"[：:|]", title_tag)[0].strip()
    cat_name = re.sub(r"价格$", "", cat_name).strip() or slug
    m = re.search(r"<table.*?</table>", page, re.S)
    if not m: print("no table", slug); continue
    trs = re.findall(r"<tr.*?</tr>", m.group(0), re.S)
    n = 0
    for r in trs[1:]:
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)
        if len(cells) < 4: continue
        txt = [H.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c))).strip() for c in cells]
        stock_txt, channel, raw_title, price_txt = txt[0], txt[1], txt[2], txt[3]
        pm = re.search(r"([\d.,]+)", price_txt)
        if not pm: continue
        price = float(pm.group(1).replace(",", ""))
        stock = 1 if stock_txt.startswith("有货") else (0 if "缺货" in stock_txt or "无货" in stock_txt else -1)
        # channel like: 链动小铺 · 牟利ai · 2VWX76A4 收录 44天前 ；或 Kami · example.com 收录 93天前（域名即店铺）
        cm = re.match(r"(.+?) · (.+?) · ([A-Za-z0-9_-]+)", channel)
        if cm:
            plat_raw, shop_name, shop_id = cm.group(1).strip(), cm.group(2).strip(), cm.group(3).strip()
        else:
            parts = [p.strip() for p in channel.split("·")]
            plat_raw = parts[0] if parts else ""
            domain = re.sub(r"\s*收录.*$", "", parts[1]).strip() if len(parts) > 1 else ""
            shop_name, shop_id = domain, domain
        platform = PLATFORM_MAP.get(plat_raw, plat_raw if plat_raw == "Kami" else "自建站")
        links = [clean_url(u) for u in re.findall(r'href="([^"]+)"', r)]
        item_url = next((u for u in links if "/item/" in u or "/goods/" in u or "pay.ldxp" in u), "")
        if not item_url:
            item_url = next((u for u in links if u.startswith("http") and "biwu.ai" not in u and "/shop/" not in u), "")
        shop_url = next((u for u in links if "/shop/" in u), "")
        if not shop_url and shop_id and "." in shop_id:
            shop_url = f"https://{shop_id}/"
        if platform == "wzyp" and shop_id and not shop_url:
            shop_url = f"https://wzyp.cn/shop/{shop_id}"
        rows.append({
            "title": raw_title, "price": price, "market_price": None, "stock": stock,
            "shop_name": shop_name, "platform": platform, "source": "BiWu",
            "category": cat_name, "item_url": item_url, "shop_url": shop_url,
            "shop_id": shop_id.lower() if platform in ("wzyp", "云猫") else shop_id,
            "goods_id": (re.search(r"/item/([a-z0-9]+)", item_url).group(1) if "/item/" in item_url else ""),
            "observed_at": now,
        }); n += 1
    print(slug, cat_name, n)
json.dump(rows, open("raw/biwu.json","w"), ensure_ascii=False, indent=1)
print("TOTAL biwu rows:", len(rows))
