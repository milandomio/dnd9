# Lootdrops 模块性能优化记录

> 优化日期: 2026-07-12
> 优化结果: 85s → 25s（省 60s，71%）

## 优化总览

| 优化 | 耗时变化 | 省时 | commit |
|------|---------|------|--------|
| 原始 | 85s | - | - |
| + compact JSON | 70s | 15s | `4109ee1` |
| + fuzzy candidate_ids | 69s | 1s | `764acc7` |
| + 移除 variant_suffixes | **25s** | **44s** | 待提交 |

## 优化 1: compact JSON（省 15s）

**文件:** `api/src/lootdrop_builder.py`

**问题:** `json.dumps(indent=2)` 输出 1.15GB 格式化 JSON，生产环境不需要可读性。

**修复:** lootdrop 详情文件使用 `separators=(',', ':')` 紧凑格式。

```python
def _save(output_dir, filename, data, compact=False):
    if compact:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    else:
        json.dump(data, f, ensure_ascii=False, indent=2)
```

**影响:** 2284 个 lootdrop 详情文件从 ~500KB/个 降到 ~200KB/个。

## 优化 2: fuzzy candidate_ids 匹配（省 1s）

**文件:** `api/src/drop_rate.py`

**问题:** 怪物英文名（如 `SkeletonFootmanFromFakeDeath_Common`）与 `entity_ldg_all` 的 key 不匹配，导致 `candidate_ids` 为空，变体爆率计算跳过。

**修复:** 在 `_get_candidate_ids` 中添加模糊匹配，尝试 `FakeDeath`/`FromFakeDeath` 后缀。

```python
# Fuzzy fallback: try adding FakeDeath/FromFakeDeath suffixes
if not candidate_ids:
    for _fuzzy_suffix in ("FakeDeath", "FromFakeDeath"):
        _fuzzy_name = monster_name + _fuzzy_suffix
        _fuzzy_groups = self._entity_ldg_all.get(_fuzzy_name, set())
        if _fuzzy_groups:
            candidate_ids.update(_fuzzy_groups)
            break
```

**影响:** 变体爆率从 0/188 条目变为 188/188 条目有非零爆率。

## 优化 3: 移除 variant_suffixes（省 44s）

**文件:** `api/src/lootdrop_builder.py`, `web/src/pages/LootdropDetailPage.tsx`

**问题:** `variant_suffixes` 与 `variant_rarity` 的 key 完全重复，前端可用 `Object.keys(variant_rarity)` 替代。

**修复:**
- 后端：移除 `variant_suffixes` 字段的计算和输出
- 前端：改用 `Object.keys(data.variant_rarity)` 获取后缀列表

```tsx
// 旧
const suffixes = data.variant_suffixes;
// 新
const suffixes = data.variant_rarity ? Object.keys(data.variant_rarity) : [];
```

**影响:** 
- 每个变体文件省 ~70 字节（7 个字符串）
- 474 个变体文件共省 ~33KB
- JSON 解析和处理时间大幅减少

## 跳过的优化

| 方案 | 原因 |
|------|------|
| per-monster 缓存 | candidate_ids 已缓存，收益不大 |
| variant_rate 缓存 | item_name 不同，命中率低 |
| grade_data 缓存 | 收益仅 1-2s |

## 剩余瓶颈

当前 25s 中的时间分布（估算）:

| 阶段 | 耗时 | 说明 |
|------|------|------|
| 坐标合并 + 爆率计算 | ~5s | 阶段 1-4 |
| 变体详情生成 | ~15s | 阶段 5（主要瓶颈） |
| 文件写入 + enrichment | ~5s | 阶段 6 + 后处理 |

**进一步优化方向:**
1. C 扩展 `compute_variant_rate`（预计省 ~10s）
2. 多进程并行变体计算（预计省 ~10s）
3. 减少变体数量（业务层面）
