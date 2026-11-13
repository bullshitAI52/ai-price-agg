# AI聚合比价空间

把散布在各个卡网（发卡平台）和 AI 代充聚合站的 AI 订阅/账号商品（ChatGPT、Claude、Gemini、Grok、Cursor 等的代充、成品号、卡密、车位）聚合到一张表里，方便按关键词、平台、店铺、价格、库存快速比价。

**只做信息聚合，不卖货、不下单、不登录任何账号。** 最终价格与库存以原站为准。

配套的静态网页空间「AI聚合比价空间」（Muse 空间，侧边栏）用同一份 `data/data.json` 渲染：关键词搜索、平台/来源/分类/店铺筛选、只看有货、价格区间与升降序、每页 100 件分页，筛选可叠加。线上空间的数据以独立文件发布、页面以 `no-store` 方式加载；`web/` 里放的是该空间导出的自包含 HTML 存档（单文件，数据已内联，仅作存档）。

## 数据（首期，2026-11-13）

- 去重后 **4123 件**商品，覆盖 **734 家**店铺
- 平台分布：wzyp（链动小铺）2128 / 云猫 1614 / 自建站 145 / 16688 114 / Kami 95 / 独角数卡 27
- 库存分布：有货 3775 / 缺货 348 / 未公开 0
- 每个数字都能从 `data/data.json` 复算，口径与明细见 `report.md`

## 数据源与抓取

| 来源 | 方式 | 脚本 |
| --- | --- | --- |
| 云猫寄售 catfk.com | 公开接口 `POST /shopApi/Shop/goodsList` 逐店直抓（店铺名单来自 AI价网店铺索引；注意：必须带 `goods_type=card`，否则返回 0） | `collectors/collect_catfk.py` |
| AI价网 aiprice.club | 机器可读 md 层：`md/index.md` + 44 个分类页（每类有货最便宜 50 家） | `collectors/collect_aiprice.py` |
| BiWu.Ai biwu.ai | 42 个标准商品页 `products/<slug>` 的全渠道报价表 | `collectors/collect_biwu.py` |
| 水獭 shuita.xyz | 官方 MCP（npm `ai-price-mcp`，只读、免 key）：`list_all_products` / `get_offers` | `collectors/collect_shuita.py` |
| 链动小铺 wzyp.cn | 直连接口与真实浏览器均被阿里云 ESA 人机验证拦截（滑块校验未过，未反复硬试）；本期 wzyp 报价由 AI价网 + BiWu 覆盖，未单独直抓 | — |

本期水獭并入 0 行：MCP 本身正常，但其数据源对抓取机出口 IP 返回 HTTP 403，待解除后重跑脚本即可并入。

## 合并规则

- 统一字段：`title, price, market_price, stock, shop_name, platform, source, category, item_url, shop_url, shop_id, goods_id, observed_at`
- 库存口径：数字 = 库存件数；0 = 缺货；只有「有货/缺货」标记的源有货记 1、缺货记 0；未知记 -1。水獭价格为含手续费到手价。
- 去重键：平台 + 店铺标识 + 商品标识；无商品标识时用「平台 + 店铺标识 + 原始标题（去空白）+ 价格」。优先级：直抓 > 水獭 > BiWu > AI价网，同商品保留直抓行。

## 复现

```bash
# 采集脚本按「脚本与 raw/ 同级」的布局编写：把 collectors/*.py 复制到一个工作目录，
# 在该目录建 raw/ 后依次运行，原始结果会写入 raw/
python3 collect_catfk.py
python3 collect_aiprice.py
python3 collect_biwu.py
python3 collect_shuita.py   # 需要 npx / node
# 把 merge.py 放到同一工作目录运行，它读 raw/ 并在同目录生成 data.json 与 report.md
python3 merge.py            # 生成的 data.json 对应仓库的 data/data.json
```

## 目录

```
collectors/   四个数据源的采集脚本
merge.py      去重合并 + 生成 report.md
data/         data.json（合并去重后的最终数据）
raw/          各源原始数据（aiprice.json / catfk.json / biwu.json / shuita*.json / aiprice_index.md）
report.md     数据报告（总数、各源净增、平台/库存分布，全部可复算）
web/          比价空间导出的自包含 HTML 存档
```

## 署名与许可红线

- **AI价网（aiprice.club）** 数据为 **CC BY 4.0**：使用须注明来源「AI价网（aiprice.club）」并附链接 https://aiprice.club 。
- **水獭 shuita.xyz**：仅并入派生报价行并署名「水獭 shuita.xyz」，禁止整站镜像、不搬运其文章。https://shuita.xyz
- **BiWu.Ai**：报价行署名「BiWu.Ai」。https://biwu.ai
- **CardNav（cardnav.xyz）、PriceAI（priceai.cc）**：其 DATA_LICENSE 明确禁止批量复制、镜像和用作替代数据源，本项目**未并入**其数据，仅可用于发现店铺、交叉核对。
- 商品信息来自各店铺公开接口/页面，版权归原店铺与来源站所有；本仓库代码可自由使用，数据部分请遵守各来源的许可与署名要求。
