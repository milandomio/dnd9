# HARDCODED_TRANSLATIONS 全量 10 语 i18n 计划

> 状态：**仅计划，未执行**  
> 日期：2026-07-26  
> 前置：`SUPERHOARD_I18N.md` 已落地（单 key 特例）；本计划将其**推广为全量框架**

---

## 1. 问题

### 1.1 现象

- `HARDCODED_TRANSLATIONS`（`api/src/config.py`）约 **230** 条，**仅 zh-Hans 中文**。
- 无 Game.json 的实体在详情/列表/掉落源常为 `translation_key=""`。
- 前端 `t(key, fallback)`：`key` 空 → 直接 `fallback`（中文真值）→ **en 等语言页仍显示中文**。

### 1.2 键值识别风险（为何不能「直接塞 10 语」）

| 风险 | 说明 | 结论 |
|------|------|------|
| **裸实体名作 locale key** | 当前 locale 几乎全是 `Text_*` / 少量 `df5.*`，裸名暂无碰撞，但与未来 key、搜索、调试不稳定 | **禁止** |
| **中文短语作 key** | 11 组同文案多实体（如 5×「超级宝藏堆」、4×「海底骷髅尸体」）；前端按实体查 key，合并会丢实体粒度 | **禁止作主键**（值可相同） |
| **与 `Text_*` 重复** | ~22 条 HARDCODED 实际已有 Game.json（别名/大小写），再造合成 key 会双轨 | **优先用已有 `Text_*`，不造 df5** |
| **locale used_keys 过滤** | `locale_builder` 只导出「被引用」的 key；只扩字典不赋 `translation_key` → 注入后仍被滤掉 | **必须同时：合成 key + 实体赋 key + locale 注入** |
| **`HARDCODED` 仅 resolve fallback** | `NameResolver` 用 HARDCODED 填 `translation`（中文），**不写** `translation_key` | 前端 i18n 看不到 |
| **坐标 `label` 中文硬写** | `index_export` / `module_builder`：`label = HARDCODED.get(keyword, keyword)`，无 key | 地图 label 仍中文（次优先，可二期） |
| **variant_names 空 key** | `collector` 对无 entity_class/monster 行写 `translation_key: ""`，name 已是中文 resolve 结果 | 需在 resolve 路径赋合成 key |
| **SuperHoard 特例** | 已用 `df5.hardcoded.SuperHoard` + 5 名共用；全量改为**每实体一名一 key** 时，SuperHoard 可保留共用或改为 5 key 同文案 | 见 §3.3 |

### 1.3 现状数据（执行前快照）

- HARDCODED：**230**；有 Game.json 前缀匹配：**~22**；无官方 key：**~208**
- `search_index` 空 `translation_key`：**~167**（其中 HARDCODED 命中 **~91**，多为 decoration）
- locale 已有：`df5.hardcoded.SuperHoard` × 10 语
- 同中文多实体共享短语：**11** 组

---

## 2. 已定决策（用户确认）

| 项 | 选择 |
|----|------|
| 范围 | **全量 230 条**（含装饰/引擎内部） |
| 合成 key | **`df5.hardcoded.{EntityName}`**（与 `Text_*` / `ui.*` 隔离） |
| 文案 | **AI 批量起草 10 语**整词（不运行时拼接）；可后续人工改 |
| SuperHoard | 已落地共用 key；全量落地时**保留** `df5.hardcoded.SuperHoard` 作为 5 名别名目标，或映射表指向同一文案（见 §3.3） |

支持语言（与 `discover_languages()` 一致）：

`zh-Hans` / `zh-Hant` / `en` / `de` / `es` / `fr` / `ja` / `ko` / `pt-BR` / `ru`

---

## 3. 目标架构

### 3.1 键规则

```
有 Game.json（含 TRANSLATION_ALIAS_MAP）→ 继续用 Text_DesignData_* 官方 key
无 Game.json 且在 HARDCODED 中     → df5.hardcoded.{ExactEntityName}
SuperHoard*（历史）                → df5.hardcoded.SuperHoard（5 名 → 同一 key，文案「超级宝藏堆」）
```

- **一实体一 key**（SuperHoard 组除外）：即使中文相同，`ChestLarge` / `ChestMedium` 仍分 key，值可同可不同。
- 命名空间 **`df5.hardcoded.*`** 保证：
  - 不与 `Text_*` 冲突
  - 不与 `ui.*` 冲突
  - `used_keys` / 前端 `t()` 可稳定识别
  - 调试时一眼可辨「非官方、站内硬编码」

### 3.2 数据结构（建议）

```python
# config.py（示意）

HARDCODED_I18N_PREFIX = "df5.hardcoded."

# 保留现有：name → 中文（resolve_name / 管道 fallback）
HARDCODED_TRANSLATIONS: dict[str, str] = { ... }  # zh-Hans 真值

# 新增：name → 10 语（或仅「无 Text_ 的子集」）
# 形式 A（推荐）：嵌套
HARDCODED_I18N: dict[str, dict[str, str]] = {
    "Barrel": {
        "zh-Hans": "木桶",
        "zh-Hant": "木桶",
        "en": "Barrel",
        ...
    },
    ...
}

# 形式 B：扁平 key
# "df5.hardcoded.Barrel": { "zh-Hans": "...", "en": "..." }

def hardcoded_translation_key(name: str) -> str | None:
    """SuperHoard* → SUPERHOARD_I18N_KEY；其余 HARDCODED 且无官方 key → df5.hardcoded.{name}"""
    ...

def hardcoded_i18n_bundle() -> dict[str, dict[str, str]]:
    """供 locale_builder：{ full_key: { lang: text } }"""
    ...
```

- `HARDCODED_TRANSLATIONS[name]` 必须等于 `HARDCODED_I18N[name]["zh-Hans"]`（单源或构建时断言）。
- 已有官方 `Text_*` 的 ~22 条：**不写** `df5` 条目；`hardcoded_translation_key` 返回 `None`，走 DB/Game key。

### 3.3 SuperHoard 与全量关系

| 方案 | 做法 |
|------|------|
| **A 保留特例（推荐，改动小）** | `superhoard_translation_key()` 优先；全量表可省略 5 个 SuperHoard 名或指向同一 `SUPERHOARD_I18N` |
| B 全部一实体一 key | 5 个 `df5.hardcoded.SuperHoard01_9` 等 + 同文案；删共用 key，需改已写入的 JSON |

执行时默认 **方案 A**。

### 3.4 数据流（改造后）

```
实体名
  → DB translation_key（Text_*）若有
  → superhoard_translation_key / hardcoded_translation_key
  → 写入 JSON translation_key
  → locale_builder：used_keys 扫到 df5.* + 强制注入 HARDCODED_I18N 全量
  → 前端 t(df5.hardcoded.X, 中文fallback)
```

`NameResolver.resolve`：仍用 HARDCODED 填中文 `translation`；**调用方**负责带上合成 key（与现 SuperHoard 一致）。

---

## 4. 实现步骤（有空再执行）

### 阶段 0 — 预检 / checkpoint

1. `git` 工作区干净或按 `DEVELOPMENT_WORKFLOW.md` 建 checkpoint。
2. 脚本统计：HARDCODED ∩ Game.json、空 tk 列表、locale 体积基线。

### 阶段 1 — 键体系 + 配置

1. `config.py`
   - `HARDCODED_I18N_PREFIX` / `hardcoded_translation_key(name)` / `hardcoded_i18n_for_locale()`
   - 将 230 条扩成 `HARDCODED_I18N`（10 语）；AI 起草后人工抽检高频用户可见名
   - 有 `Text_*` 的条目：不进合成 key 路径（函数内查 Game 或静态 denylist）
   - SuperHoard：保持现有常量，全量函数里 `superhoard` 优先
2. 可选：大表拆到 `api/src/hardcoded_i18n.py` 或 `api/src/data/hardcoded_i18n.json`，`config` 只 re-export（避免 config.py 过长）

### 阶段 2 — 赋 key（后端写出路径）

凡写入 `translation_key` 且可能为空处，统一：

```python
tk = existing or superhoard_translation_key(name) or hardcoded_translation_key(name) or ""
```

优先改：

| 文件 | 点 |
|------|-----|
| `locale_builder.py` | 注入全部 `df5.hardcoded.*`（或 used ∪ 全量 HARDCODED keys）；泛化现 SuperHoard 单条注入 |
| `module_builder.py` | `entity_class` / SuperHoard 注入泛化为「空 tk + HARDCODED → 合成 key」；`entity_index.json` |
| `lootdrop_builder.py` | 掉落源 / `monster_translation_keys` / SuperHoard 分支改用通用 `hardcoded_translation_key` |
| `collector.py` | `coord_variant_count` 的 variant_names：无 mrow 时用合成 key，勿只 `""` |
| `entity_export.py` | props/monsters 空 tk 时补合成 key（如 LivingStatue props 行、SuperHoard01_9） |
| `index_export.py` | search_index 空 tk 补 key；**label 中文**二期可改 `label_key`（本期可不改地图 label） |
| `quest_collector.py` | 若用 HARDCODED 且对外 JSON 有 tk 字段则对齐 |
| `translator.py` | 可选：`resolve` 不改返回值；或增加 `resolve_key(name) -> str` 供调用方 |

**不改**（除非二期）：坐标点 `label` 字符串本身（仍中文/英文 keyword）；前端地图图例若只显示 label 仍中文。

### 阶段 3 — locale 注入

```python
# locale_builder.build_locale_files
for full_key, lang_map in hardcoded_i18n_bundle().items():
    used_keys.add(full_key)  # 或不过滤强制写入
    filtered[full_key] = lang_map.get(lang) or lang_map.get("zh-Hans")
# SuperHoard 单条逻辑合并进 bundle，避免两套注入
```

- 体积：+~208 key × 10 语，约数十 KB 级，可接受。
- 有官方 key 的 HARDCODED 中文仅作 resolve fallback，**不**进 df5 bundle。

### 阶段 4 — 文案质量

1. AI 批量：以 `HARDCODED_TRANSLATIONS` 中文为语义，整词译 9 语 + 繁中。
2. 抽检优先级：lootdrop 源、props 列表、search 可见 > 纯 decoration/引擎名。
3. 游戏内已有近似名（如 Hoard、Chest）可对齐官方 en 用词风格。
4. `MODULE_NAME_OVERRIDE`（EmptyModule 显示名）**不在**本期 HARDCODED 全量内；若要做另开 `df5.module.*`。

### 阶段 5 — 验证

- [ ] `python main.py` EXIT:0
- [ ] `locale/en.json` 含抽样 `df5.hardcoded.Barrel`、`df5.hardcoded.ChestLarge` 等非中文
- [ ] `df5.hardcoded.SuperHoard` 仍在且文案不变
- [ ] `search_index`：原 HARDCODED 空 tk 条目现有 `df5.hardcoded.*` 或官方 `Text_*`
- [ ] Ruby_5001 等：SuperHoard + 原空 key 掉落源 en 非中文
- [ ] props `LivingStatue` / `SkeletonWoodenBarrel` 等有 key
- [ ] 前端 dev：`/en/...` 抽样页
- [ ] `SESSION_CHANGES.md` + 本地 commit（不 push）

### 阶段 6 — 文档

- 本文件状态改为「已执行」并勾选步骤
- 可在 `MULTILANG_PLAN.md` 加一句：无 Game.json 实体用 `df5.hardcoded.*`
- SuperHoard 计划保留作历史特例说明

---

## 5. 明确不做（本期）

- 不把 HARDCODED 写进 DB `translations_*` 表（避免污染官方表；locale 注入足够）
- 不用中文或裸名当 locale 主键
- 不运行时字符串拼接多语言（整词表）
- 不强制改坐标 `label` 展示（二期：`label` + `label_key`）
- 不翻译 `MODULE_NAME_OVERRIDE` / UI `ui.*`（已有 uiLocale）
- 不 push 远程

---

## 6. 键冲突速查（执行时遵守）

```
Text_DesignData_*     → 游戏官方
ui.*                  → 前端 UI
df5.hardcoded.*       → 站内无官方 key 的实体名
df5.hardcoded.SuperHoard → SuperHoard* 共用（历史）
```

前端：`mergedDict[key] ?? fallback`；只要 key 非空且 locale 有值即可，**无**键识别逻辑改动需求。

---

## 7. 工作量粗估

| 块 | 量 |
|----|-----|
| 键函数 + locale 注入泛化 | 小（0.5h） |
| 各 builder 赋 key | 中（2–4h，点多） |
| 230 × 9 语 AI 表 + 抽检 | 中（主要体积在 config/数据文件） |
| 管道验证 | 中（一次 full pipeline） |

---

## 8. 参考

- `docs/plans/SUPERHOARD_I18N.md` — 已落地特例
- `docs/plans/MULTILANG_PLAN.md` — translation_key / locale 总设计
- `docs/plans/DUNGEON_GROUP_I18N.md` — 存 key 不存拼好的中文
- `api/src/locale_builder.py` / `config.py` / `translator.py` / `lootdrop_builder.py`
