# Lootdrop 品质变体 JSON 合并计划

## 状态

草案，未执行。当前 `_1001` 至 `_7001` 独立详情 JSON 与 Cloudflare `404.html` 接管保持不变，直到本计划完成数据语义验证。

## 目标

- 每个普通 lootdrop 家族仅导出一个详情 JSON，删除 `_1001` 至 `_7001` 的独立详情文件。
- 坐标只由对应怪物或容器实体 JSON 提供，不再内联复制到 lootdrop 详情。
- 品质差异以“容器实体在地图分组中是否产出该品质及其爆率”表达，而非按单个 spawner 点位过滤。
- 变体切换复用已加载的基底详情，不再请求另一份 lootdrop 变体 JSON。
- 保持现有变体 URL、独立 `_8001` 条目、地图展示、分组爆率与语言路由语义。

## 现状与问题

`api/src/lootdrop_builder.py` 当前为每个 `_1001` 至 `_7001` 品质导出完整详情。它会复制怪物元数据、分地图 `group_drop_info`、`variant_rarity`，且对没有 `ref` 的容器内联已按 spawner label 筛过的坐标。

以 `HeaterShield` 为例：基底详情含 53 个怪物/容器、8 个地图分组和约 3,000 个内联坐标；其中 40 个已有实体 `ref`，另有 13 个条目保留内联坐标。分地图爆率仅 175 条记录，不是主要体积来源。`_5001` 又复制约 2,713 个内联坐标。

当前内联坐标是为了避免前端加载 `ref` 后显示该实体的全部点位。前端只按地图模块过滤 `ref` 坐标，尚未按当前品质的有效地图分组过滤。

## 目标数据模型

普通家族详情统一为 `lootdrops/{base}.json`：

```json
{
  "name": "HeaterShield",
  "translation_key": "...",
  "variant_rarity": { "1001": { "translation_key": "..." } },
  "sources": {
    "source-id": {
      "entity_name": "WoodChestMedium",
      "ref": "props/WoodChestMedium",
      "translation_key": "...",
      "color": "#..."
    }
  },
  "variants": {
    "5001": {
      "group_drop_info": {
        "Inferno": [
          {
            "source_id": "source-id",
            "spawn_rate": 100,
            "drop_rates": { "PVE": 0, "普通": 0, "豪客赛": 4.6154 }
          }
        ]
      }
    }
  }
}
```

约束：

- `source_id` 必须稳定，不能以中文 `translation` 关联。相同 `entity_name` 在不同逻辑来源出现时必须保留可区分 ID。
- 每个 `source` 必须有可公开请求的 `ref`。无法映射实体页面的来源应使构建失败并输出清单，不再回退内联坐标。
- `variants[suffix].group_drop_info` 是该品质的唯一权威：它同时决定有效容器、有效地图分组、spawn rate 和各模式爆率。
- `_8001` 是独立 lootdrop 条目，不纳入普通家族 `variants`。

## 客户端合并规则

1. 从 URL 的 `name` 解析基底名和品质后缀；无后缀维持既有默认品质选择。
2. 只请求 `/data/{version}/json/lootdrops/{base}.json`。
3. 从 `variants[suffix].group_drop_info` 建立 `source_id -> 有效地图分组 -> 爆率` 映射。
4. 仅请求当前品质有效来源的实体 `ref` 坐标；复用现有全局 ref 缓存。
5. 将每个坐标的 `map` 映射为地图分组，只保留该来源在当前品质有效的分组；不再按 spawner label 裁点。
6. 使用该地图分组的 `spawn_rate × 豪客赛 drop_rate / 100` 重算坐标 `score` 和来源 `max_score`。
7. 由已合并数据继续驱动现有地图、容器分类、参考爆率和稀有度切换 UI。

## 生成端改造

- `api/src/lootdrop_builder.py`：将当前变体循环从“每 suffix 写完整 `variant_detail`”改为收集 `variants[suffix].group_drop_info`。
- 导出基础 `sources` 与 `entity_page_map` 的稳定映射；对每个 source 强制填充 `ref`。
- 停止写 `lootdrops/{base}_{suffix}.json`，仅保留普通基底和独立 `_8001` 文件。
- 在构建中输出并校验：变体 source 集合、地图分组集合、合并后 score/max_score 与旧 JSON 的语义对比。

## 前端与 SSG 改造

- `web/src/pages/LootdropDetailPage.tsx`：按基底请求并在内存中合并当前 suffix；扩展 ref 坐标过滤为来源级地图分组过滤。
- `web/src/types/data.ts`：定义 `LootdropSource`、`LootdropVariantData`、带 `source_id` 的分组爆率类型。
- `web/src/components/VariantSwitch.tsx`：保持现有路径 URL，只改变页面数据选择，不再要求对应 suffix JSON 存在。
- `web/scripts/ssg.mjs`：变体详情壳的 preload 指向基底 JSON；路由/404 裁剪策略无需因本计划改变。
- PWA：版本化 URL 与现有 runtime cache 规则保持；切换品质不新增 lootdrop 请求，实体 `ref` 继续走全局缓存。

## 请求与体积预算

- 确定收益：普通变体详情文件从 1,831 个降为 0；每家族仅保留一个基底详情，减少部署文件数和重复 JSON 字节。
- 确定收益：同一页面切换品质不再请求新的 lootdrop JSON。
- 首次访问不应宣称必然减少请求：此前内联坐标的 13 类来源改为 `ref` 后可能增加实体 JSON 请求。
- 首开请求预算以“仅请求当前品质有效 source 的 ref + 全局缓存去重”为准；若实测劣于现状，需要评估批量坐标端点或保留特定来源的紧凑共享坐标包，不能重新复制完整变体详情。
- 验收必须比较冷缓存首开、同家族切换、跨家族访问的请求数、传输字节、渲染完成时间和 Workbox 缓存条目数。

## 验收与回退

- 抽样比较旧 `_1001`、`_5001`、`_7001` 与合并后页面的有效地图分组、来源、坐标数、score、max_score、参考爆率。
- 特别覆盖同一 `entity_name` 多逻辑来源、容器、宝藏堆、拟态怪、`ref` 怪物和独立 `_8001`。
- 确认不存在 `lootdrops/{base}_{suffix}.json` 后，旧 URL 仍能加载对应品质数据。
- 若地图分组过滤导致坐标语义偏离，或首开请求/传输明显回退，则停止删除旧变体文件并回退本计划。
