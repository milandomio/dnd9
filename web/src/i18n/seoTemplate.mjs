const COPY = {
  'zh-Hans': {
    home: 'DarkFlashNav 是《越来越黑暗》游戏数据导航，提供物品、怪物、掉落来源、地图坐标、NPC 任务与地牢模块的可搜索查询，帮助你在每次探险前快速定位资源和目标。',
    list: ({ category, count }) =>
      `浏览《越来越黑暗》${category}${count ? `，收录 ${count} 个条目` : ''}。查看详细地图位置、坐标与相关掉落信息，使用 DarkFlashNav 快速规划下一次地牢探索。`,
    entity: ({ name, locations }) =>
      `${name} 的《越来越黑暗》地图位置${locations ? `，目前记录 ${locations} 个位置点` : ''}。通过 DarkFlashNav 查看生成分布、坐标与相关掉落信息，快速找到目标资源。`,
    lootdrop: ({ name, sources, locations }) =>
      `${name} 的《越来越黑暗》掉落来源${sources ? `，来自 ${sources} 个来源` : ''}${locations ? `，覆盖 ${locations} 个位置点` : ''}。查看怪物、地图坐标和掉落详情，为地牢探索规划路线。`,
    explore: ({ targets, npcs }) =>
      `《越来越黑暗》探索任务目标汇总${targets ? `，包含 ${targets} 个目标` : ''}${npcs ? `，关联 ${npcs} 个 NPC` : ''}。按任务和地图模块查询目标位置，快速完成探索任务。`,
    questItems: ({ groups, locations }) =>
      `《越来越黑暗》任务物品位置查询${groups ? `，覆盖 ${groups} 个地图分组` : ''}${locations ? `和 ${locations} 个位置点` : ''}。按地图查找 Fetch 任务物品、实体和坐标。`,
    questGroup: ({ name, entities, locations }) =>
      `${name} 的《越来越黑暗》任务物品位置${entities ? `，包含 ${entities} 个任务实体` : ''}${locations ? `和 ${locations} 个位置点` : ''}。查看地图分布和坐标，完成 NPC 收集任务。`,
    questNpcs: ({ npcs }) =>
      `《越来越黑暗》NPC 任务列表${npcs ? `，包含 ${npcs} 个活跃 NPC` : ''}。浏览任务链、收集目标、奖励和前置条件，使用筛选快速规划任务进度。`,
    questNpc: ({ name, quests }) =>
      `${name} 的《越来越黑暗》任务详情${quests ? `，包含 ${quests} 个任务` : ''}。查看任务链、收集目标、奖励、前置条件与完成建议，规划你的冒险进度。`,
    modules: ({ groups, modules }) =>
      `《越来越黑暗》地牢地图模块查询${groups ? `，覆盖 ${groups} 个地图分组` : ''}${modules ? `和 ${modules} 个模块` : ''}。浏览模块布局、实体分布和地图坐标，快速识别探索区域。`,
    moduleGroup: ({ name, modules }) =>
      `${name} 的《越来越黑暗》地图模块${modules ? `，收录 ${modules} 个模块` : ''}。查看模块布局、可用实体和坐标信息，为地牢探索与资源搜索规划路线。`,
    module: ({ name, group, width, height, entities, locations }) =>
      `${name} 的《越来越黑暗》地图模块详情${group ? `，属于 ${group}` : ''}${width && height ? `，尺寸 ${width}x${height}` : ''}${entities ? `，包含 ${entities} 个实体` : ''}${locations ? `和 ${locations} 个位置点` : ''}。查看布局与坐标。`,
    categories: {
      items: '物品',
      monsters: '怪物',
      props: '实体',
      lootdrops: '掉落物',
    },
  },
  en: {
    home: 'DarkFlashNav is a Dark and Darker reference for interactive maps, item and monster locations, loot sources, NPC quests, quest objectives, dungeon modules, and searchable coordinate data.',
    list: ({ category, count }) =>
      `Browse ${count ? `${count} ` : ''}${category} in Dark and Darker. Open detailed map locations, coordinates, and related loot data in DarkFlashNav to plan your next dungeon run.`,
    entity: ({ name, locations }) =>
      `${name} in Dark and Darker${locations ? ` has ${locations} recorded map locations` : ''}. Use DarkFlashNav to inspect known spawns, coordinates, and related loot information before entering the dungeon.`,
    lootdrop: ({ name, sources, locations }) =>
      `${name} loot sources in Dark and Darker${sources ? ` include ${sources} source entries` : ''}${locations ? ` across ${locations} map locations` : ''}. Review monsters, coordinates, and drop details to plan your route.`,
    explore: ({ targets, npcs }) =>
      `Dark and Darker exploration objectives${targets ? ` with ${targets} targets` : ''}${npcs ? ` across ${npcs} NPCs` : ''}. Find quest targets by map module and complete exploration tasks efficiently.`,
    questItems: ({ groups, locations }) =>
      `Dark and Darker quest item locations${groups ? ` across ${groups} map groups` : ''}${locations ? ` and ${locations} positions` : ''}. Find Fetch quest items, entities, and coordinates by map.`,
    questGroup: ({ name, entities, locations }) =>
      `${name} quest item locations in Dark and Darker${entities ? ` with ${entities} quest entities` : ''}${locations ? ` and ${locations} positions` : ''}. Inspect maps and coordinates to complete NPC collection tasks.`,
    questNpcs: ({ npcs }) =>
      `Dark and Darker NPC quests${npcs ? ` for ${npcs} active NPCs` : ''}. Browse quest chains, collection objectives, rewards, prerequisites, and filters to plan your progression.`,
    questNpc: ({ name, quests }) =>
      `${name} quests in Dark and Darker${quests ? ` include ${quests} quests` : ''}. Review quest chains, objectives, rewards, prerequisites, and completion guidance for your adventure.`,
    modules: ({ groups, modules }) =>
      `Dark and Darker dungeon modules${groups ? ` across ${groups} map groups` : ''}${modules ? ` and ${modules} modules` : ''}. Browse layouts, entity distributions, and map coordinates to identify exploration areas.`,
    moduleGroup: ({ name, modules }) =>
      `${name} dungeon modules in Dark and Darker${modules ? ` include ${modules} modules` : ''}. Inspect layouts, available entities, and coordinates to plan dungeon exploration and resource searches.`,
    module: ({ name, group, width, height, entities, locations }) =>
      `${name} dungeon module in Dark and Darker${group ? ` for ${group}` : ''}${width && height ? `, sized ${width}x${height}` : ''}${entities ? ` with ${entities} entities` : ''}${locations ? ` and ${locations} positions` : ''}. Inspect its layout and coordinates.`,
    categories: {
      items: 'items',
      monsters: 'monsters',
      props: 'props',
      lootdrops: 'loot drops',
    },
  },
  de: {
    home: 'DarkFlashNav ist ein Dark-and-Darker-Nachschlagewerk mit interaktiven Karten, Fundorten von Gegenständen und Monstern, Beutequellen, NPC-Quests, Zielen, Dungeon-Modulen und durchsuchbaren Koordinaten.',
    list: ({ category, count }) =>
      `Durchsuche ${count ? `${count} ` : ''}${category} in Dark and Darker. Öffne Kartenpositionen, Koordinaten und Beutedaten in DarkFlashNav und plane deinen nächsten Dungeonlauf.`,
    entity: ({ name, locations }) =>
      `${name} in Dark and Darker${locations ? ` mit ${locations} bekannten Kartenpositionen` : ''}. DarkFlashNav zeigt Spawnorte, Koordinaten und zugehörige Beuteinformationen für deine Erkundung.`,
    lootdrop: ({ name, sources, locations }) =>
      `${name}-Beutequellen in Dark and Darker${sources ? ` mit ${sources} Quellen` : ''}${locations ? ` an ${locations} Kartenpositionen` : ''}. Prüfe Monster, Koordinaten und Beutedetails für deine Route.`,
    explore: ({ targets, npcs }) =>
      `Dark-and-Darker-Erkundungsziele${targets ? ` mit ${targets} Zielen` : ''}${npcs ? ` bei ${npcs} NPCs` : ''}. Finde Questziele nach Kartenmodul und erledige Erkundungsaufgaben gezielt.`,
    questItems: ({ groups, locations }) =>
      `Dark-and-Darker-Questgegenstände${groups ? ` in ${groups} Kartengruppen` : ''}${locations ? ` an ${locations} Positionen` : ''}. Finde Fetch-Gegenstände, Entitäten und Koordinaten nach Karte.`,
    questGroup: ({ name, entities, locations }) =>
      `${name}-Questgegenstände in Dark and Darker${entities ? ` mit ${entities} Questentitäten` : ''}${locations ? ` und ${locations} Positionen` : ''}. Prüfe Karten und Koordinaten für NPC-Sammelaufgaben.`,
    questNpcs: ({ npcs }) =>
      `Dark-and-Darker-NPC-Quests${npcs ? ` für ${npcs} aktive NPCs` : ''}. Durchsuche Questketten, Sammelziele, Belohnungen und Voraussetzungen für deinen Fortschritt.`,
    questNpc: ({ name, quests }) =>
      `${name}-Quests in Dark and Darker${quests ? ` mit ${quests} Quests` : ''}. Prüfe Questketten, Ziele, Belohnungen, Voraussetzungen und Hinweise zum Abschließen.`,
    modules: ({ groups, modules }) =>
      `Dark-and-Darker-Dungeon-Module${groups ? ` in ${groups} Kartengruppen` : ''}${modules ? ` mit ${modules} Modulen` : ''}. Durchsuche Layouts, Entitäten und Kartenkoordinaten für die Erkundung.`,
    moduleGroup: ({ name, modules }) =>
      `${name}-Dungeon-Module in Dark and Darker${modules ? ` mit ${modules} Modulen` : ''}. Prüfe Layouts, verfügbare Entitäten und Koordinaten für Erkundung und Ressourcensuche.`,
    module: ({ name, group, width, height, entities, locations }) =>
      `${name}-Dungeon-Modul in Dark and Darker${group ? ` für ${group}` : ''}${width && height ? ` mit Größe ${width}x${height}` : ''}${entities ? ` und ${entities} Entitäten` : ''}${locations ? ` an ${locations} Positionen` : ''}. Prüfe Layout und Koordinaten.`,
    categories: {
      items: 'Gegenstände',
      monsters: 'Monster',
      props: 'Objekte',
      lootdrops: 'Beute',
    },
  },
  es: {
    home: 'DarkFlashNav es una guía de Dark and Darker con mapas interactivos, ubicaciones de objetos y monstruos, fuentes de botín, misiones de NPC, objetivos, módulos de mazmorra y coordenadas buscables.',
    list: ({ category, count }) =>
      `Explora ${count ? `${count} ` : ''}${category} de Dark and Darker. Abre ubicaciones, coordenadas y datos de botín detallados en DarkFlashNav para planear tu próxima incursión.`,
    entity: ({ name, locations }) =>
      `${name} en Dark and Darker${locations ? ` tiene ${locations} ubicaciones registradas` : ''}. Usa DarkFlashNav para revisar apariciones, coordenadas e información de botín relacionada.`,
    lootdrop: ({ name, sources, locations }) =>
      `Fuentes de botín de ${name} en Dark and Darker${sources ? ` con ${sources} fuentes` : ''}${locations ? ` y ${locations} ubicaciones` : ''}. Revisa monstruos, coordenadas y detalles de botín para tu ruta.`,
    explore: ({ targets, npcs }) =>
      `Objetivos de exploración de Dark and Darker${targets ? ` con ${targets} objetivos` : ''}${npcs ? ` para ${npcs} NPC` : ''}. Encuentra objetivos por módulo de mapa y completa misiones de exploración.`,
    questItems: ({ groups, locations }) =>
      `Ubicaciones de objetos de misión de Dark and Darker${groups ? ` en ${groups} grupos de mapas` : ''}${locations ? ` y ${locations} posiciones` : ''}. Encuentra objetos, entidades y coordenadas de misiones Fetch.`,
    questGroup: ({ name, entities, locations }) =>
      `Objetos de misión de ${name} en Dark and Darker${entities ? ` con ${entities} entidades` : ''}${locations ? ` y ${locations} posiciones` : ''}. Consulta mapas y coordenadas para completar encargos de NPC.`,
    questNpcs: ({ npcs }) =>
      `Misiones de NPC de Dark and Darker${npcs ? ` para ${npcs} NPC activos` : ''}. Consulta cadenas, objetivos, recompensas y requisitos para planear tu progreso.`,
    questNpc: ({ name, quests }) =>
      `Misiones de ${name} en Dark and Darker${quests ? ` con ${quests} misiones` : ''}. Consulta objetivos, recompensas, requisitos y consejos de finalización.`,
    modules: ({ groups, modules }) =>
      `Módulos de mazmorra de Dark and Darker${groups ? ` en ${groups} grupos de mapas` : ''}${modules ? ` y ${modules} módulos` : ''}. Consulta diseños, entidades y coordenadas para explorar.`,
    moduleGroup: ({ name, modules }) =>
      `Módulos de mazmorra de ${name} en Dark and Darker${modules ? ` con ${modules} módulos` : ''}. Consulta diseños, entidades disponibles y coordenadas para explorar y buscar recursos.`,
    module: ({ name, group, width, height, entities, locations }) =>
      `Módulo ${name} de Dark and Darker${group ? ` para ${group}` : ''}${width && height ? `, tamaño ${width}x${height}` : ''}${entities ? `, ${entities} entidades` : ''}${locations ? ` y ${locations} posiciones` : ''}. Consulta diseño y coordenadas.`,
    categories: {
      items: 'objetos',
      monsters: 'monstruos',
      props: 'entidades',
      lootdrops: 'botines',
    },
  },
  fr: {
    home: 'DarkFlashNav est un guide Dark and Darker avec cartes interactives, positions d’objets et de monstres, sources de butin, quêtes de PNJ, objectifs, modules de donjon et coordonnées consultables.',
    list: ({ category, count }) =>
      `Parcourez ${count ? `${count} ` : ''}${category} dans Dark and Darker. Ouvrez les positions, coordonnées et données de butin détaillées avec DarkFlashNav pour préparer votre prochaine expédition.`,
    entity: ({ name, locations }) =>
      `${name} dans Dark and Darker${locations ? ` compte ${locations} positions répertoriées` : ''}. Utilisez DarkFlashNav pour consulter apparitions, coordonnées et informations de butin associées.`,
    lootdrop: ({ name, sources, locations }) =>
      `Sources de butin de ${name} dans Dark and Darker${sources ? ` avec ${sources} sources` : ''}${locations ? ` et ${locations} positions` : ''}. Consultez monstres, coordonnées et détails du butin pour préparer votre trajet.`,
    explore: ({ targets, npcs }) =>
      `Objectifs d’exploration Dark and Darker${targets ? ` avec ${targets} objectifs` : ''}${npcs ? ` pour ${npcs} PNJ` : ''}. Trouvez les objectifs par module de carte et terminez les quêtes d’exploration.`,
    questItems: ({ groups, locations }) =>
      `Positions des objets de quête Dark and Darker${groups ? ` dans ${groups} groupes de cartes` : ''}${locations ? ` et ${locations} positions` : ''}. Trouvez objets Fetch, entités et coordonnées par carte.`,
    questGroup: ({ name, entities, locations }) =>
      `Objets de quête ${name} dans Dark and Darker${entities ? ` avec ${entities} entités` : ''}${locations ? ` et ${locations} positions` : ''}. Consultez cartes et coordonnées pour les collectes de PNJ.`,
    questNpcs: ({ npcs }) =>
      `Quêtes de PNJ Dark and Darker${npcs ? ` pour ${npcs} PNJ actifs` : ''}. Consultez chaînes de quêtes, objectifs, récompenses et prérequis pour planifier votre progression.`,
    questNpc: ({ name, quests }) =>
      `Quêtes de ${name} dans Dark and Darker${quests ? ` avec ${quests} quêtes` : ''}. Consultez objectifs, récompenses, prérequis et conseils de progression.`,
    modules: ({ groups, modules }) =>
      `Modules de donjon Dark and Darker${groups ? ` dans ${groups} groupes de cartes` : ''}${modules ? ` et ${modules} modules` : ''}. Consultez agencements, entités et coordonnées pour explorer.`,
    moduleGroup: ({ name, modules }) =>
      `Modules de donjon ${name} dans Dark and Darker${modules ? ` avec ${modules} modules` : ''}. Consultez agencements, entités disponibles et coordonnées pour explorer et chercher des ressources.`,
    module: ({ name, group, width, height, entities, locations }) =>
      `Module ${name} de Dark and Darker${group ? ` pour ${group}` : ''}${width && height ? `, taille ${width}x${height}` : ''}${entities ? `, ${entities} entités` : ''}${locations ? ` et ${locations} positions` : ''}. Consultez agencement et coordonnées.`,
    categories: {
      items: 'objets',
      monsters: 'monstres',
      props: 'entités',
      lootdrops: 'butins',
    },
  },
  ja: {
    home: 'DarkFlashNav は、インタラクティブマップ、アイテムとモンスターの出現場所、ドロップ元、NPC クエスト、目標、ダンジョンモジュール、検索可能な座標を提供する Dark and Darker のデータガイドです。',
    list: ({ category, count }) =>
      `Dark and Darker の${category}${count ? `を ${count} 件` : ''}閲覧できます。DarkFlashNav で詳細なマップ位置、座標、関連ドロップ情報を確認し、次の探索を計画しましょう。`,
    entity: ({ name, locations }) =>
      `Dark and Darker の${name}${locations ? `の記録済みマップ位置は ${locations} 件です` : 'のマップ位置'}。DarkFlashNav で出現場所、座標、関連ドロップ情報を確認できます。`,
    lootdrop: ({ name, sources, locations }) =>
      `Dark and Darker の${name}のドロップ元${sources ? `は ${sources} 件` : ''}${locations ? `、マップ位置は ${locations} 件` : ''}です。モンスター、座標、ドロップ詳細を確認して探索ルートを計画できます。`,
    explore: ({ targets, npcs }) =>
      `Dark and Darker の探索目標${targets ? ` ${targets} 件` : ''}${npcs ? `、NPC ${npcs} 人` : ''}をまとめています。マップモジュール別に目標位置を探し、探索クエストを効率よく完了できます。`,
    questItems: ({ groups, locations }) =>
      `Dark and Darker のクエストアイテム位置${groups ? `を ${groups} のマップグループ` : ''}${locations ? `、${locations} 地点` : ''}で確認できます。Fetch クエストのアイテム、エンティティ、座標を地図別に検索できます。`,
    questGroup: ({ name, entities, locations }) =>
      `Dark and Darker の${name}クエストアイテム位置${entities ? `、${entities} エンティティ` : ''}${locations ? `、${locations} 地点` : ''}です。NPC 収集クエスト用のマップと座標を確認できます。`,
    questNpcs: ({ npcs }) =>
      `Dark and Darker の NPC クエスト${npcs ? `、アクティブ NPC ${npcs} 人` : ''}を閲覧できます。クエスト連鎖、収集目標、報酬、前提条件を確認して進行を計画できます。`,
    questNpc: ({ name, quests }) =>
      `Dark and Darker の${name}クエスト${quests ? ` ${quests} 件` : ''}です。クエスト連鎖、目標、報酬、前提条件、完了のヒントを確認できます。`,
    modules: ({ groups, modules }) =>
      `Dark and Darker のダンジョンモジュール${groups ? `、${groups} のマップグループ` : ''}${modules ? `、${modules} モジュール` : ''}を閲覧できます。レイアウト、エンティティ、座標から探索エリアを確認できます。`,
    moduleGroup: ({ name, modules }) =>
      `Dark and Darker の${name}ダンジョンモジュール${modules ? ` ${modules} 件` : ''}です。レイアウト、利用可能なエンティティ、座標を確認して探索と資源探しを計画できます。`,
    module: ({ name, group, width, height, entities, locations }) =>
      `Dark and Darker の${name}ダンジョンモジュール詳細${group ? `、${group}` : ''}${width && height ? `、サイズ ${width}x${height}` : ''}${entities ? `、${entities} エンティティ` : ''}${locations ? `、${locations} 地点` : ''}。レイアウトと座標を確認できます。`,
    categories: {
      items: 'アイテム',
      monsters: 'モンスター',
      props: 'エンティティ',
      lootdrops: 'ドロップ',
    },
  },
  ko: {
    home: 'DarkFlashNav는 대화형 지도, 아이템과 몬스터 위치, 드롭 출처, NPC 퀘스트, 목표, 던전 모듈 및 검색 가능한 좌표를 제공하는 Dark and Darker 데이터 가이드입니다.',
    list: ({ category, count }) =>
      `Dark and Darker의 ${category}${count ? ` ${count}개` : ''}를 살펴보세요. DarkFlashNav에서 상세 지도 위치, 좌표 및 관련 드롭 정보를 확인하고 다음 던전 탐험을 계획하세요.`,
    entity: ({ name, locations }) =>
      `Dark and Darker의 ${name}${locations ? `은 기록된 지도 위치가 ${locations}개입니다` : '의 지도 위치'}。DarkFlashNav에서 생성 위치, 좌표 및 관련 드롭 정보를 확인하세요.`,
    lootdrop: ({ name, sources, locations }) =>
      `Dark and Darker ${name} 드롭 출처${sources ? ` ${sources}개` : ''}${locations ? `, 지도 위치 ${locations}개` : ''}입니다. 몬스터, 좌표 및 드롭 세부 정보를 확인해 탐험 경로를 계획하세요.`,
    explore: ({ targets, npcs }) =>
      `Dark and Darker 탐험 목표${targets ? ` ${targets}개` : ''}${npcs ? `, NPC ${npcs}명` : ''}을 정리했습니다. 지도 모듈별 목표 위치를 찾아 탐험 퀘스트를 완료하세요.`,
    questItems: ({ groups, locations }) =>
      `Dark and Darker 퀘스트 아이템 위치${groups ? ` ${groups}개 지도 그룹` : ''}${locations ? `, ${locations}개 위치` : ''}입니다. Fetch 퀘스트 아이템, 엔티티, 좌표를 지도별로 찾으세요.`,
    questGroup: ({ name, entities, locations }) =>
      `Dark and Darker ${name} 퀘스트 아이템 위치${entities ? `, ${entities}개 엔티티` : ''}${locations ? `, ${locations}개 위치` : ''}입니다. NPC 수집 퀘스트용 지도와 좌표를 확인하세요.`,
    questNpcs: ({ npcs }) =>
      `Dark and Darker NPC 퀘스트${npcs ? `, 활성 NPC ${npcs}명` : ''}입니다. 퀘스트 연계, 수집 목표, 보상 및 선행 조건을 확인해 진행을 계획하세요.`,
    questNpc: ({ name, quests }) =>
      `Dark and Darker ${name} 퀘스트${quests ? ` ${quests}개` : ''}입니다. 퀘스트 연계, 목표, 보상, 선행 조건 및 완료 안내를 확인하세요.`,
    modules: ({ groups, modules }) =>
      `Dark and Darker 던전 모듈${groups ? ` ${groups}개 지도 그룹` : ''}${modules ? `, ${modules}개 모듈` : ''}입니다. 레이아웃, 엔티티 분포 및 지도 좌표로 탐험 지역을 확인하세요.`,
    moduleGroup: ({ name, modules }) =>
      `Dark and Darker ${name} 던전 모듈${modules ? ` ${modules}개` : ''}입니다. 레이아웃, 사용 가능한 엔티티, 좌표를 확인해 탐험과 자원 탐색을 계획하세요.`,
    module: ({ name, group, width, height, entities, locations }) =>
      `Dark and Darker ${name} 던전 모듈 상세${group ? `, ${group}` : ''}${width && height ? `, 크기 ${width}x${height}` : ''}${entities ? `, ${entities}개 엔티티` : ''}${locations ? `, ${locations}개 위치` : ''}입니다. 레이아웃과 좌표를 확인하세요.`,
    categories: {
      items: '아이템',
      monsters: '몬스터',
      props: '엔티티',
      lootdrops: '드롭',
    },
  },
  'pt-BR': {
    home: 'DarkFlashNav é uma referência de Dark and Darker com mapas interativos, locais de itens e monstros, fontes de saque, missões de NPC, objetivos, módulos de masmorra e coordenadas pesquisáveis.',
    list: ({ category, count }) =>
      `Navegue por ${count ? `${count} ` : ''}${category} em Dark and Darker. Abra locais no mapa, coordenadas e dados de saque detalhados no DarkFlashNav para planejar sua próxima expedição.`,
    entity: ({ name, locations }) =>
      `${name} em Dark and Darker${locations ? ` possui ${locations} locais registrados no mapa` : ''}. Use o DarkFlashNav para consultar aparições, coordenadas e informações de saque relacionadas.`,
    lootdrop: ({ name, sources, locations }) =>
      `Fontes de saque de ${name} em Dark and Darker${sources ? ` com ${sources} fontes` : ''}${locations ? ` e ${locations} locais no mapa` : ''}. Consulte monstros, coordenadas e detalhes de saque para planejar sua rota.`,
    explore: ({ targets, npcs }) =>
      `Objetivos de exploração de Dark and Darker${targets ? ` com ${targets} objetivos` : ''}${npcs ? ` para ${npcs} NPCs` : ''}. Encontre objetivos por módulo de mapa e conclua missões de exploração.`,
    questItems: ({ groups, locations }) =>
      `Locais de itens de missão de Dark and Darker${groups ? ` em ${groups} grupos de mapas` : ''}${locations ? ` e ${locations} posições` : ''}. Encontre itens Fetch, entidades e coordenadas por mapa.`,
    questGroup: ({ name, entities, locations }) =>
      `Itens de missão de ${name} em Dark and Darker${entities ? ` com ${entities} entidades` : ''}${locations ? ` e ${locations} posições` : ''}. Consulte mapas e coordenadas para tarefas de coleta de NPCs.`,
    questNpcs: ({ npcs }) =>
      `Missões de NPC de Dark and Darker${npcs ? ` para ${npcs} NPCs ativos` : ''}. Consulte cadeias, objetivos, recompensas e pré-requisitos para planejar seu progresso.`,
    questNpc: ({ name, quests }) =>
      `Missões de ${name} em Dark and Darker${quests ? ` com ${quests} missões` : ''}. Consulte objetivos, recompensas, pré-requisitos e orientações de conclusão.`,
    modules: ({ groups, modules }) =>
      `Módulos de masmorra de Dark and Darker${groups ? ` em ${groups} grupos de mapas` : ''}${modules ? ` e ${modules} módulos` : ''}. Consulte layouts, entidades e coordenadas para explorar.`,
    moduleGroup: ({ name, modules }) =>
      `Módulos de masmorra de ${name} em Dark and Darker${modules ? ` com ${modules} módulos` : ''}. Consulte layouts, entidades disponíveis e coordenadas para exploração e recursos.`,
    module: ({ name, group, width, height, entities, locations }) =>
      `Módulo ${name} de Dark and Darker${group ? ` para ${group}` : ''}${width && height ? `, tamanho ${width}x${height}` : ''}${entities ? `, ${entities} entidades` : ''}${locations ? ` e ${locations} posições` : ''}. Consulte layout e coordenadas.`,
    categories: {
      items: 'itens',
      monsters: 'monstros',
      props: 'entidades',
      lootdrops: 'saques',
    },
  },
  ru: {
    home: 'DarkFlashNav — справочник Dark and Darker с интерактивными картами, местами предметов и монстров, источниками добычи, заданиями NPC, целями, модулями подземелий и поиском по координатам.',
    list: ({ category, count }) =>
      `Просматривайте ${count ? `${count} ` : ''}${category} в Dark and Darker. Открывайте точки на карте, координаты и данные о добыче в DarkFlashNav для планирования следующего похода.`,
    entity: ({ name, locations }) =>
      `${name} в Dark and Darker${locations ? `: записано ${locations} точек на карте` : ''}. Используйте DarkFlashNav, чтобы посмотреть места появления, координаты и связанную добычу.`,
    lootdrop: ({ name, sources, locations }) =>
      `Источники добычи ${name} в Dark and Darker${sources ? `: ${sources} источников` : ''}${locations ? `, ${locations} точек на карте` : ''}. Изучайте монстров, координаты и детали добычи для маршрута.`,
    explore: ({ targets, npcs }) =>
      `Цели исследования Dark and Darker${targets ? `: ${targets} целей` : ''}${npcs ? ` у ${npcs} NPC` : ''}. Находите цели по модулям карты и эффективно выполняйте задания исследования.`,
    questItems: ({ groups, locations }) =>
      `Места предметов заданий Dark and Darker${groups ? ` в ${groups} группах карт` : ''}${locations ? `, ${locations} позиций` : ''}. Находите предметы Fetch, сущности и координаты по карте.`,
    questGroup: ({ name, entities, locations }) =>
      `Предметы заданий ${name} в Dark and Darker${entities ? `: ${entities} сущностей` : ''}${locations ? `, ${locations} позиций` : ''}. Изучайте карты и координаты для заданий NPC на сбор.`,
    questNpcs: ({ npcs }) =>
      `Задания NPC Dark and Darker${npcs ? ` для ${npcs} активных NPC` : ''}. Просматривайте цепочки, цели сбора, награды и требования для планирования прогресса.`,
    questNpc: ({ name, quests }) =>
      `Задания ${name} в Dark and Darker${quests ? `: ${quests} заданий` : ''}. Просматривайте цели, награды, требования и подсказки по выполнению.`,
    modules: ({ groups, modules }) =>
      `Модули подземелий Dark and Darker${groups ? ` в ${groups} группах карт` : ''}${modules ? `, ${modules} модулей` : ''}. Просматривайте схемы, сущности и координаты для исследования.`,
    moduleGroup: ({ name, modules }) =>
      `Модули подземелий ${name} в Dark and Darker${modules ? `: ${modules} модулей` : ''}. Просматривайте схемы, доступные сущности и координаты для поиска ресурсов.`,
    module: ({ name, group, width, height, entities, locations }) =>
      `Модуль ${name} в Dark and Darker${group ? ` для ${group}` : ''}${width && height ? `, размер ${width}x${height}` : ''}${entities ? `, ${entities} сущностей` : ''}${locations ? ` и ${locations} точек` : ''}. Просматривайте схему и координаты.`,
    categories: {
      items: 'предметы',
      monsters: 'монстров',
      props: 'сущности',
      lootdrops: 'добычу',
    },
  },
  'zh-Hant': {
    home: 'DarkFlashNav 是《越來越黑暗》遊戲資料導航，提供物品、怪物、掉落來源、地圖座標、NPC 任務與地城模組的可搜尋查詢，協助你在每次探險前快速定位資源與目標。',
    list: ({ category, count }) =>
      `瀏覽《越來越黑暗》${category}${count ? `，收錄 ${count} 個項目` : ''}。查看詳細地圖位置、座標與相關掉落資訊，使用 DarkFlashNav 快速規劃下一次地城探索。`,
    entity: ({ name, locations }) =>
      `${name} 的《越來越黑暗》地圖位置${locations ? `，目前記錄 ${locations} 個位置點` : ''}。透過 DarkFlashNav 查看生成分布、座標與相關掉落資訊，快速找到目標資源。`,
    lootdrop: ({ name, sources, locations }) =>
      `${name} 的《越來越黑暗》掉落來源${sources ? `，來自 ${sources} 個來源` : ''}${locations ? `，涵蓋 ${locations} 個位置點` : ''}。查看怪物、地圖座標與掉落詳情，規劃地城探索路線。`,
    explore: ({ targets, npcs }) =>
      `《越來越黑暗》探索任務目標總覽${targets ? `，包含 ${targets} 個目標` : ''}${npcs ? `，關聯 ${npcs} 個 NPC` : ''}。按任務與地圖模組查詢目標位置，快速完成探索任務。`,
    questItems: ({ groups, locations }) =>
      `《越來越黑暗》任務物品位置查詢${groups ? `，涵蓋 ${groups} 個地圖分組` : ''}${locations ? `與 ${locations} 個位置點` : ''}。按地圖尋找 Fetch 任務物品、實體與座標。`,
    questGroup: ({ name, entities, locations }) =>
      `${name} 的《越來越黑暗》任務物品位置${entities ? `，包含 ${entities} 個任務實體` : ''}${locations ? `與 ${locations} 個位置點` : ''}。查看地圖分布與座標，完成 NPC 收集任務。`,
    questNpcs: ({ npcs }) =>
      `《越來越黑暗》NPC 任務列表${npcs ? `，包含 ${npcs} 個活躍 NPC` : ''}。瀏覽任務鏈、收集目標、獎勵與前置條件，使用篩選快速規劃任務進度。`,
    questNpc: ({ name, quests }) =>
      `${name} 的《越來越黑暗》任務詳情${quests ? `，包含 ${quests} 個任務` : ''}。查看任務鏈、收集目標、獎勵、前置條件與完成建議，規劃冒險進度。`,
    modules: ({ groups, modules }) =>
      `《越來越黑暗》地城地圖模組查詢${groups ? `，涵蓋 ${groups} 個地圖分組` : ''}${modules ? `與 ${modules} 個模組` : ''}。瀏覽模組布局、實體分布與地圖座標，快速辨識探索區域。`,
    moduleGroup: ({ name, modules }) =>
      `${name} 的《越來越黑暗》地圖模組${modules ? `，收錄 ${modules} 個模組` : ''}。查看模組布局、可用實體與座標資訊，規劃地城探索與資源搜尋路線。`,
    module: ({ name, group, width, height, entities, locations }) =>
      `${name} 的《越來越黑暗》地圖模組詳情${group ? `，屬於 ${group}` : ''}${width && height ? `，尺寸 ${width}x${height}` : ''}${entities ? `，包含 ${entities} 個實體` : ''}${locations ? `與 ${locations} 個位置點` : ''}。查看布局與座標。`,
    categories: {
      items: '物品',
      monsters: '怪物',
      props: '實體',
      lootdrops: '掉落物',
    },
  },
};

export function buildSeoDescription(lang, type, facts = {}) {
  const locale = COPY[lang] || COPY['zh-Hans'];
  const template = locale[type] || locale.home;
  if (typeof template !== 'function') return template;
  return template({
    ...facts,
    category: locale.categories[facts.category] || facts.category,
  });
}
