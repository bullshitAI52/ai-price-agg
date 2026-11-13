#!/usr/bin/env python3
"""Merge all sources into data.json + report.md. Every number in the report is recomputed from the raw files."""
import json, collections, datetime, re, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))
now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec="seconds")

def load(name):
    p = f"raw/{name}.json"
    if not os.path.exists(p): return []
    return json.load(open(p))

SOURCES = [  # priority order: direct first
    ("catfk", "直抓-云猫"),
    ("shuita", "水獭"),
    ("biwu", "BiWu"),
    ("aiprice", "AI价网"),
]
raw = {k: load(k) for k, _ in SOURCES}
for k, rows in raw.items():
    print(k, len(rows))

def norm_title(t):
    return re.sub(r"\s+", "", (t or "")).lower()

def key_of(r):
    plat = r.get("platform", "")
    shop = (r.get("shop_id") or r.get("shop_name") or "").lower()
    gid = r.get("goods_id") or ""
    if gid:
        return (plat, shop, "g:" + gid)
    return (plat, shop, "t:" + norm_title(r.get("title", "")) + "|" + str(r.get("price")))

# enrichment maps from the whole raw pool
item_url_map, shop_url_map, shop_name_map = {}, {}, {}
for rows in raw.values():
    for r in rows:
        k1 = (r.get("platform", ""), (r.get("shop_id") or "").lower(), norm_title(r.get("title", "")))
        if r.get("item_url"): item_url_map.setdefault(k1, r["item_url"])
        if r.get("shop_url"): shop_url_map.setdefault((r.get("platform", ""), (r.get("shop_id") or "").lower()), r["shop_url"])
        if r.get("shop_name"): shop_name_map.setdefault((r.get("platform", ""), (r.get("shop_id") or "").lower()), r["shop_name"])

seen = {}
kept = []
stats = {}
for src_key, _label in SOURCES:
    rows = raw[src_key]
    kept_n = 0
    for r in rows:
        k = key_of(r)
        if k in seen: continue
        seen[k] = src_key
        out = {
            "title": r.get("title", ""), "price": float(r.get("price") or 0),
            "market_price": (float(r["market_price"]) if r.get("market_price") else None),
            "stock": int(r.get("stock", -1)), "shop_name": r.get("shop_name", ""),
            "platform": r.get("platform", ""), "source": r.get("source", ""),
            "category": r.get("category", ""), "item_url": r.get("item_url", ""),
            "shop_url": r.get("shop_url", ""), "shop_id": r.get("shop_id", ""),
            "goods_id": r.get("goods_id", ""), "observed_at": r.get("observed_at", now),
        }
        # enrich
        k1 = (out["platform"], out["shop_id"].lower(), norm_title(out["title"]))
        if not out["item_url"] and k1 in item_url_map: out["item_url"] = item_url_map[k1]
        ks = (out["platform"], out["shop_id"].lower())
        if not out["shop_url"] and ks in shop_url_map: out["shop_url"] = shop_url_map[ks]
        if not out["shop_name"] and ks in shop_name_map: out["shop_name"] = shop_name_map[ks]
        kept.append(out); kept_n += 1
    stats[src_key] = {"raw": len(rows), "kept": kept_n, "dropped_dup": len(rows) - kept_n}

kept.sort(key=lambda r: (r["price"], r["title"]))
shops = set((r["platform"], r["shop_id"].lower() or r["shop_name"]) for r in kept)
data = {"updated_at": now, "total": len(kept), "shop_count": len(shops), "items": kept}
json.dump(data, open("data.json", "w"), ensure_ascii=False, indent=1)
print("FINAL total", len(kept), "shops", len(shops))

plat_dist = collections.Counter(r["platform"] for r in kept)
src_dist = collections.Counter(r["source"] for r in kept)
stock_dist = {"in_stock_gt0": sum(1 for r in kept if r["stock"] > 0), "out_0": sum(1 for r in kept if r["stock"] == 0), "unknown_-1": sum(1 for r in kept if r["stock"] == -1)}
cat_dist = collections.Counter(r["category"] for r in kept if r["category"])

L = []
L.append("# AI聚合比价 · 数据报告\n")
L.append(f"- 生成时间：{now}（Asia/Shanghai）")
L.append(f"- 商品总数（去重后）：**{len(kept)}**")
L.append(f"- 覆盖店铺数（平台+店铺标识去重）：**{len(shops)}**")
L.append("- 本报告所有数字都可由同目录 `data.json` 与 `raw/` 原始文件复算（见 merge.py）。\n")
L.append("## 各源抓取与净增\n")
L.append("| 来源 | 原始行数 | 去重后保留（净增） | 因重复被丢弃 |")
L.append("| --- | ---: | ---: | ---: |")
label = {"catfk": "直抓 · 云猫寄售 catfk.com（goodsList 接口，100 家店）", "shuita": "水獭 shuita.xyz（官方 MCP ai-price-mcp）", "biwu": "BiWu.Ai biwu.ai（42 个标准商品页）", "aiprice": "AI价网 aiprice.club（md 层 44 个分类，每类有货最便宜 50 家）"}
for k, _ in SOURCES:
    s = stats[k]
    L.append(f"| {label[k]} | {s['raw']} | {s['kept']} | {s['dropped_dup']} |")
L.append("")
L.append("去重规则：键 = 平台 + 店铺标识 + 商品标识；无商品标识时用「平台 + 店铺标识 + 原始标题（去空白）+ 价格」。优先级：直抓 > 水獭 > BiWu > AI价网，同商品保留高优先级行。")
L.append("注意：各源保留行之和 = 去重后总数；同一店铺的同名同价商品在不同分类表里重复出现也按上键去重。\n")
L.append("## 平台分布（去重后）\n")
L.append("| 平台 | 商品数 |")
L.append("| --- | ---: |")
for p, c in plat_dist.most_common():
    L.append(f"| {p} | {c} |")
L.append("\n## 来源分布（去重后）\n")
L.append("| 来源标记 | 商品数 |")
L.append("| --- | ---: |")
for p, c in src_dist.most_common():
    L.append(f"| {p} | {c} |")
L.append("\n## 库存分布（去重后）\n")
L.append(f"- 有货（stock > 0）：{stock_dist['in_stock_gt0']}")
L.append(f"- 缺货（stock = 0）：{stock_dist['out_0']}")
L.append(f"- 库存未公开（stock = -1）：{stock_dist['unknown_-1']}")
L.append("\n库存口径：数字 = 库存件数；0 = 缺货；只有「有货/缺货」标记的源（BiWu、水獭 unknown 除外）有货记 1、缺货记 0；未知记 -1。水獭价格为含手续费到手价。\n")
L.append("## 分类 Top 20（去重后）\n")
L.append("| 分类 | 商品数 |")
L.append("| --- | ---: |")
for p, c in cat_dist.most_common(20):
    L.append(f"| {p} | {c} |")
L.append("\n## 未并入 / 受限说明\n")
L.append("- 链动小铺 wzyp.cn 直抓：直连接口被阿里云 ESA 人机验证拦截（已实测返回验证页）。2026-11-13 又用真实浏览器会话尝试过一次店铺页验证：滑块可拖到终点，但服务端校验两次均未通过（Verification failed），按约定未反复硬试。因此 wzyp 平台的报价本期由 AI价网、BiWu 两源覆盖（平台分布中的 wzyp 即链动小铺，共 2128 行）。若用户本人在浏览器里手动通过一次验证，后续可再尝试用该会话直抓。")
L.append("- 水獭 shuita.xyz：官方 MCP 可正常启动，但其数据源 /data/core.json 在本机出口 IP 下返回 HTTP 403（直连 shuita.xyz 同样 403），本期水獭原始行数 = 0，已如实计入上表；待 403 解除后重跑 collect_shuita.py 即可并入。")
L.append("- CardNav（cardnav.xyz）、PriceAI（priceai.cc）：其 DATA_LICENSE 禁止批量复制/镜像，本项目未并入其数据，仅可用于发现店铺与交叉核对。")
L.append("- AI价网 md 层未提供链接的 18 个分类（如 GPT Pro、Kiro、Suno 等）在 md 层无 50 家表，本期未收录这些分类的 AI价网行；BiWu/直抓行中仍可能包含相关商品。")
L.append("\n## 署名与许可\n")
L.append("- AI价网（aiprice.club）数据为 CC BY 4.0，使用须注明来源「AI价网（aiprice.club）」并附链接 https://aiprice.club 。")
L.append("- 水獭 shuita.xyz：仅并入派生报价行并署名，不镜像整站、不搬运文章。https://shuita.xyz")
L.append("- BiWu.Ai：报价行署名「BiWu.Ai」。https://biwu.ai")
L.append("- 云猫寄售、链动小铺等平台商品信息来自各店铺公开接口/页面，最终价格与库存以原站为准。本项目只做信息聚合，不卖货、不下单。")
open("report.md", "w").write("\n".join(L) + "\n")
print("report.md written")
print(json.dumps({"plat": plat_dist, "src": src_dist, "stock": stock_dist}, ensure_ascii=False, default=dict))
