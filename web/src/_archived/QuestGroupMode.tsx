/**
 * 归档：【任务物品表】分组详情页的 quest_group 模式。
 *
 * 迁移日期：2026-10-25
 * 迁移原因：用户要求把【任务物品表】栏目的代码存档、不再使用，并从主页移除入口。
 *           `LootdropDetailPage` 原本通过 `mode="quest_group"` 复用掉落详情页渲染
 *           `/quest_items/:group`，这部分分支已从活跃代码中摘除，内容记录在此。
 *
 * 恢复方式（按顺序）：
 *   1. `web/src/AppInner.tsx` 加回：
 *        <Route path="/:lang/quest_items" element={<QuestItemsPage />} />
 *        <Route path="/:lang/quest_items/:group" element={<LootdropDetailPage mode="quest_group" />} />
 *   2. `web/src/pages/LootdropDetailPage.tsx` 恢复下面的类型、`normalizeQuestGroup()`、
 *      props 里的 `mode`、`isQuestGroupPage` 分支、`quest_items_groups` 数据加载、
 *      以及标题/SEO 的 `questGroup` 分支；
 *   3. `web/src/main.tsx` 恢复 `hasRouteSsrData()` 的
 *      `if (page === 'quest_items' && parts[1]) return Boolean(ssrData[\`quest_items_groups/\${parts[1]}\`]);`
 *   4. `web/src/components/NavBar.tsx` 恢复 `NAV_LABEL_KEYS.quest_items` 与
 *      `PAGE_TAG_KEYS.quest_items`；
 *   5. `web/scripts/ssg.mjs` 恢复 `SINGLE` / `DETAIL_TEMPLATE_PAGES` 的 `'quest_items'`、
 *      `questGroups` 路由、`ssrDataMap` 注入、`routeDataKey` 分支、
 *      `localizedQuestGroupTitle()`、`GROUP_FLOOR_SUFFIX`、`templateDescription` 分支；
 *   6. 后端恢复 `api/src/_archived/quest_items_groups_export.py` 的
 *      `generate_quest_items_groups()` 及 `collector.py` 中的调用。
 *
 * 未归档（仍活跃）：`quest_items` 数据表、`save_quest_data()` 的 `quest_items.json`
 * 导出（管道内部文件，交付时跳过）、`ui.quest_items.*` /
 * `ui.home.card_labels.quest_items` / `ui.home.view_quest_items` /
 * `ui.nav.quest_items` / `ui.search.tag.quest` 文案键、`seoTemplate` 的
 * `questItems` / `questGroup` 模板——保留以便恢复，不影响构建。
 *
 * ─────────────── 以下为摘除的代码原文（仅供参考，未参与编译） ───────────────
 *
 * interface QuestGroupEntity {
 *   name: string;
 *   translation: string;
 *   translation_key?: string;
 *   color: string;
 *   coords: LootdropCoord[];
 * }
 *
 * interface QuestGroupData {
 *   group: string;
 *   group_key?: string;
 *   group_floor?: number;
 *   group_sub_key?: string | null;
 *   group_display: string;
 *   entities: QuestGroupEntity[];
 * }
 *
 * function normalizeQuestGroup(group: QuestGroupData): LootdropItem {
 *   return {
 *     name: group.group,
 *     translation: group.group_display,
 *     monsters: group.entities.map((entity) => ({
 *       name: entity.name,
 *       entity_name: entity.name,
 *       translation: entity.translation,
 *       translation_key: entity.translation_key,
 *       source_id: entity.name,
 *       color: entity.color,
 *       coords: entity.coords,
 *     })),
 *   };
 * }
 *
 * // 组件签名
 * interface LootdropDetailPageProps {
 *   mode?: 'lootdrop' | 'quest_group';
 * }
 * export default function LootdropDetailPage({ mode = 'lootdrop' }: LootdropDetailPageProps) {
 *   const { name, group } = useParams<{ name: string; group: string }>();
 *   const isQuestGroupPage = mode === 'quest_group';
 *   const decodedName = decodeURIComponent((isQuestGroupPage ? group : name) ?? '');
 *   const variantMatch = isQuestGroupPage ? null : decodedName.match(VARIANT_RE);
 *   const dataKey = isQuestGroupPage ? `quest_items_groups/${decodedName}` : `lootdrops/${decodedName}`;
 *   const baseDataKey = isQuestGroupPage ? '' : `lootdrops/${baseName}`;
 *   const ssrQuestData = useSSRData<QuestGroupData>(isQuestGroupPage ? dataKey : '');
 *   const fullQuestSsrData =
 *     isQuestGroupPage && ssrQuestData?.entities?.length ? ssrQuestData : null;
 *   const questSsrItem = useMemo(
 *     () => (fullQuestSsrData ? normalizeQuestGroup(fullQuestSsrData) : null),
 *     [fullQuestSsrData]
 *   );
 *   const effectiveSsrData = useMemo(
 *     () =>
 *       isQuestGroupPage
 *         ? questSsrItem
 *           ? { item: questSsrItem, modules: [] }
 *           : null
 *         : hasLootdropDetail(ssrData?.item)
 *           ? ssrData
 *           : hasLootdropDetail(baseSsrData?.item)
 *             ? baseSsrData
 *             : ssrData?.item?.name
 *               ? ssrData
 *               : baseSsrData?.item?.name
 *                 ? baseSsrData
 *                 : null,
 *     [isQuestGroupPage, questSsrItem, ssrData, baseSsrData]
 *   );
 *   const [questGroupData, setQuestGroupData] = useState<QuestGroupData | null>(fullQuestSsrData);
 *
 *   // 数据加载（含客户端回退请求）
 *   if (isQuestGroupPage) {
 *     // SSR 命中时直接用 fullQuestSsrData，否则
 *     // fetch(dataUrl(dataVersion, `/data/json/quest_items_groups/${encodeURIComponent(decodedName)}.json`))
 *   }
 *
 *   // 标题与 SEO
 *   const questGroupLabel = questGroupData
 *     ? formatGroupLabel(questGroupData, t, ut)
 *     : data.translation || decodedName;
 *   const itemLabel = isQuestGroupPage ? questGroupLabel : stripTrailingParenthetical(...);
 *   const pageLabel = isQuestGroupPage ? ut('ui.nav.quest_items') : ut('ui.nav.lootdrops');
 *   const description = localizedSeoDescription(
 *     lang, dict, isQuestGroupPage ? 'questGroup' : 'lootdrop',
 *     isQuestGroupPage
 *       ? { name: itemLabel, entities: monsters.length || undefined, locations: rawLocationCount || undefined }
 *       : { name: itemLabel, sources: monsters.length || undefined, locations: rawLocationCount || undefined }
 *   );
 *
 *   // 掉落率筛选栏、`?sources=` 回写、CompositeRate 在 quest 模式下都需跳过：
 *   //   {!isQuestGroupPage && ( ... )}
 */

export {};
