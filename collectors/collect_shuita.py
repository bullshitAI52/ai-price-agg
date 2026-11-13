#!/usr/bin/env python3
"""Collect Shuita (shuita.xyz) derived offers via official MCP (ai-price-mcp, read-only, no key).
Only per-offer quote rows are merged; no site mirroring, no articles."""
import subprocess, json, threading, queue, datetime, re

now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec="seconds")
p = subprocess.Popen(["npx", "-y", "ai-price-mcp"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
_id = [0]
def call(method, params=None, is_notif=False):
    _id[0] += 1
    msg = {"jsonrpc": "2.0", "method": method}
    if not is_notif: msg["id"] = _id[0]
    if params is not None: msg["params"] = params
    p.stdin.write(json.dumps(msg) + "\n"); p.stdin.flush()
    if is_notif: return None
    while True:
        line = p.stdout.readline()
        if not line: return None
        try: d = json.loads(line)
        except Exception: continue
        if d.get("id") == _id[0]:
            return d.get("result")

call("initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "muse", "version": "1.0"}})
call("notifications/initialized", is_notif=True)

def tool(name, args):
    r = call("tools/call", {"name": name, "arguments": args})
    if not r: return None
    # result may be structuredContent or content text
    if "structuredContent" in r: return r["structuredContent"]
    for c in r.get("content", []):
        if c.get("type") == "text":
            try: return json.loads(c["text"])
            except Exception: return {"_text": c["text"]}
    return r

prod = tool("list_all_products", {})
products = prod.get("products", prod) if isinstance(prod, dict) else prod
if isinstance(products, dict): products = products.get("items", [])
print("shuita SKUs:", len(products))
json.dump(prod, open("raw/shuita_products.json", "w"), ensure_ascii=False, indent=1)

rows = []
for i, pr in enumerate(products):
    sku = pr.get("sku"); name = pr.get("name", sku)
    off = tool("get_offers", {"sku": sku, "limit": 20, "include_out_of_stock": True})
    offers = []
    if isinstance(off, dict):
        offers = off.get("offers") or off.get("items") or []
    if i == 0:
        json.dump(off, open("raw/shuita_offers_sample.json", "w"), ensure_ascii=False, indent=1)
        print("sample offer keys:", offers[0].keys() if offers else off)
    for o in offers:
        stock_raw = o.get("stock", "unknown")
        if stock_raw == "in_stock":
            stock = int(o.get("stock_count") or 1)
        elif stock_raw == "out":
            stock = 0
        else:
            stock = -1
        plat = o.get("platform", "")
        platform = {"ldxp": "wzyp", "wzyp": "wzyp", "catfk": "云猫", "链动小铺": "wzyp", "云猫寄售": "云猫", "16688": "16688"}.get(plat, plat or "自建站")
        token = o.get("shop_token", "")
        if platform == "wzyp" and token:
            shop_url = f"https://wzyp.cn/shop/{token}"
        elif platform == "云猫" and token:
            shop_url = f"https://catfk.com/shop/{token}"
        elif platform == "16688" and token:
            shop_url = f"https://www.16688.com.cn/shop/{token}"
        else:
            shop_url = o.get("shop_page", "")
        item_url = ""
        rows.append({
            "title": o.get("title") or o.get("product_name") or name, "price": float(o.get("price") or 0),
            "market_price": (float(o["list_price"]) if o.get("list_price") else None),
            "stock": stock, "shop_name": o.get("shop", ""), "platform": platform,
            "source": "水獭", "category": name, "item_url": item_url if item_url != shop_url else "",
            "shop_url": shop_url, "shop_id": token.lower() if platform in ("wzyp", "云猫") else token,
            "goods_id": o.get("goods_key", "") or (re.search(r"/item/([a-z0-9]+)", item_url or "") .group(1) if "/item/" in (item_url or "") else ""),
            "observed_at": o.get("checked_at") or now, "sku": sku,
        })
    if (i + 1) % 20 == 0: print(i + 1, "SKUs, rows", len(rows))
json.dump(rows, open("raw/shuita.json", "w"), ensure_ascii=False, indent=1)
print("TOTAL shuita rows:", len(rows))
p.kill()
