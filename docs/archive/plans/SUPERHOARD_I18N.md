# SuperHoard 超级宝藏/超级宝藏堆 i18n 计划

## 问题

`SuperHoard*` 无 Game.json key，`HARDCODED_TRANSLATIONS` 仅中文 → 详情/列表 `translation_key=""` → en 页显示「超级宝藏堆」。

## 策略

- **10 语整词硬编码**（不运行时拼接）；文案以 `Text_DesignData_Props_Props_Hoard` 各语为语义基准
- **全部 SuperHoard***：`SuperHoard` / `SuperHoardChest` / `SuperHoardChest01` / `SuperHoard01_9` / `SuperHoardChest01_9`
- 合成 key：`df5.hardcoded.SuperHoard`（堆）与 `df5.hardcoded.SuperHoard_Pile` 可合并为同一展示文案「超级宝藏堆」；历史「超级宝藏」与「超级宝藏堆」统一为堆文案

## 10 语文案

| lang | value |
|------|-------|
| zh-Hans | 超级宝藏堆 |
| zh-Hant | 超級寶藏堆 |
| en | Super Treasure Hoard |
| de | Super-Schatzhort |
| es | Super Pila del Tesoro |
| fr | Super Pile de Trésors |
| ja | スーパー財宝の山 |
| ko | 슈퍼 보물 더미 |
| pt-BR | Super Pilha de Tesouros |
| ru | Супер Гора Сокровищ |

合成 key：`df5.hardcoded.SuperHoard`（所有 SuperHoard* 实体共用）

## 实现步骤

1. `config.py` — 常量 `SUPERHOARD_I18N_KEY` + `SUPERHOARD_I18N` 10 语表；实体名集合
2. `locale_builder.py` — 各语言 locale 强制注入该 key
3. `lootdrop_builder.py` — 详情/索引对 SuperHoard* 赋 `translation_key`
4. `HARDCODED_TRANSLATIONS` — 中文统一为「超级宝藏堆」（resolve_name fallback）
5. 管道 + 验证 + SESSION_CHANGES

## 验证

- ✅ 管道 EXIT:0
- ✅ `locale/en.json` 含 `df5.hardcoded.SuperHoard` → Super Treasure Hoard
- ✅ Ruby_5001 SuperHoard01_9 有 translation_key；详情 empty keys=0
- 刷新 `/en/lootdrops/Ruby_5001/` 应显示 Super Treasure Hoard
