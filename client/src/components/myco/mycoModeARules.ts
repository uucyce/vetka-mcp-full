import type { MycoModeAFocusSnapshot, MycoModeAHint, MycoModeAInputs, MycoModeASurface } from './mycoModeATypes';

function inferSurface(input: MycoModeAInputs): MycoModeASurface {
  if (input.isContextMenuOpen) return 'context_menu';
  if (input.isDevPanelOpen) return 'devpanel';
  if (input.isArtifactOpen) return 'artifact';
  if (input.isChatOpen && input.chatMode === 'scanner') return 'scanner';
  if (input.isChatOpen && input.hasActiveGroup) return 'group_chat';
  if (input.isChatOpen && input.chatMode === 'group') return 'group_setup';
  if (input.isChatOpen && input.leftPanel === 'history') return 'chat_history';
  if (input.isChatOpen && input.leftPanel === 'models') return 'model_directory';
  if (input.isChatOpen) return 'chat';
  if (input.disabledSearchAttempt || input.searchContext !== 'vetka') return 'search';
  return 'tree';
}

export function createMycoModeAFocusSnapshot(input: MycoModeAInputs): MycoModeAFocusSnapshot {
  return {
    ...input,
    surface: inferSurface(input),
  };
}

export function buildMycoModeAStateKey(snapshot: MycoModeAFocusSnapshot): string {
  return [
    snapshot.surface,
    snapshot.selectedNode?.id || 'no-node',
    snapshot.leftPanel,
    snapshot.isArtifactOpen ? snapshot.artifactPath || 'artifact-open' : 'artifact-closed',
    snapshot.searchContext,
    snapshot.searchQueryEmpty ? 'search-empty' : 'search-busy',
    snapshot.chatInputEmpty ? 'chat-empty' : 'chat-busy',
    snapshot.disabledSearchAttempt || 'no-disabled-attempt',
    snapshot.treeViewMode,
  ].join('|');
}

function buildTreeHint(snapshot: MycoModeAFocusSnapshot): MycoModeAHint {
  const modeBody: Record<MycoModeAFocusSnapshot['treeViewMode'], string> = {
    directed: 'Directed Mode показывает рабочий поток и путь по веткам. Здесь лучше двигаться по папкам и переходам исполнения.',
    knowledge: 'Knowledge Mode подчеркивает связи и смысловые соседства. Здесь лучше исследовать контекст и соседние кластеры.',
    media_edit: 'Media Edit Mode готовит медиапапку к монтажному проходу. Здесь полезно открыть медиа-артефакт или дождаться startup scan.',
  };

  if (!snapshot.selectedNode && snapshot.keyInventoryLoaded && !snapshot.hasAnyKeys) {
    return {
      title: 'First run · keys missing',
      body: 'VETKA открыт, но ключи еще не добавлены. Чтобы оживить модели, открой чат, затем phonebook и drawer API Keys. Для web/ в текущем runtime нужен отдельный Tavily key. Если не хочешь управлять ключами вручную, в конце входа можно рассмотреть VETKA subscription.',
      nextActions: ['Открыть чат', 'Открыть phonebook', 'Открыть API Keys drawer и вставить первый ключ'],
      shortcuts: ['Cmd/Ctrl+Shift+D: DevPanel'],
      tone: 'warning',
    };
  }

  if (!snapshot.selectedNode) {
    return {
      title: `VETKA main surface · ${snapshot.treeViewMode}`,
      body: `${modeBody[snapshot.treeViewMode]} Выбери ноду или переключись в поиск.`,
      nextActions: ['Выбрать ноду в дереве', 'Открыть чат', 'Сменить источник поиска'],
      shortcuts: ['G: grab mode', 'Cmd/Ctrl+Shift+D: DevPanel'],
      tone: 'info',
    };
  }

  const isArtifactLike = snapshot.selectedNode.type === 'file' || snapshot.selectedNode.type === 'artifact';
  return {
    title: `Фокус: ${snapshot.selectedNode.name}`,
    body: `${modeBody[snapshot.treeViewMode]} Нода выбрана. Дальше лучше либо открыть чат для задачи, либо закрепить контекст, либо открыть артефакт.`,
    nextActions: isArtifactLike
      ? ['Открыть чат по текущей ноде', 'Открыть артефакт', 'Закрепить файл']
      : ['Открыть чат по текущей ветке', 'Раскрыть соседний контекст', 'Сменить режим дерева'],
    shortcuts: ['G: grab mode', 'Esc: выйти из grab mode'],
    tone: 'action',
  };
}

function buildModelDirectoryHint(snapshot: MycoModeAFocusSnapshot): MycoModeAHint {
  if (!snapshot.keyInventoryLoaded) {
    return {
      title: 'Model phonebook',
      body: 'Эта панель меняет реальный маршрут ответа. Выбери модель, проверь ключи и затем возвращайся в чат.',
      nextActions: ['Выбрать модель', 'Открыть API Keys drawer', 'Закрыть phonebook'],
      shortcuts: [],
      tone: 'action',
    };
  }

  if (!snapshot.hasAnyKeys) {
    return {
      title: 'Model phonebook · no keys yet',
      body: 'Это основной вход для первого запуска. Открой drawer API Keys, вставь первый ключ, и VETKA сам попробует определить провайдера. Для старта проще всего оживить модели одним LLM key, а для web/ потом отдельно добавить Tavily key. Если у провайдера есть free tier или trial quota на твоем аккаунте, начни с него. Если не хочешь разбираться с ключами вручную, можно мягко перейти на VETKA subscription.',
      nextActions: ['Открыть API Keys drawer', 'Вставить первый LLM key', 'Потом добавить Tavily key для web/'],
      shortcuts: [],
      tone: 'warning',
    };
  }

  if (!snapshot.hasLlmProviderKey) {
    return {
      title: 'Model phonebook · add model key',
      body: 'Ключи в системе уже есть, но маршрут для облачных моделей не выглядит готовым. Добавь LLM key в drawer, затем выбери модель и при желании отметь favorite key или favorite model звездой.',
      nextActions: ['Добавить LLM key', 'Выбрать favorite key', 'Выбрать favorite model'],
      shortcuts: [],
      tone: 'warning',
    };
  }

  if (snapshot.searchContext === 'web' && !snapshot.hasSearchProviderKey) {
    return {
      title: 'Model phonebook · web key missing',
      body: 'Cloud-модельный путь уже ожил, но web/ в текущем runtime работает через Tavily. Открой drawer API Keys и добавь Tavily key. Пока его нет, используй vetka/ или file/.',
      nextActions: ['Открыть API Keys drawer', 'Добавить Tavily key', 'Вернуться в web/ search'],
      shortcuts: [],
      tone: 'warning',
    };
  }

  return {
    title: 'Model phonebook',
    body: 'Маршрут ответа уже готов. Выбери модель под задачу, а если хочешь зафиксировать привычный путь, отметь favorite key или favorite model звездой.',
    nextActions: ['Выбрать модель', 'Отметить favorite key', 'Отметить favorite model'],
    shortcuts: [],
    tone: 'action',
  };
}

function buildChatHint(snapshot: MycoModeAFocusSnapshot): MycoModeAHint {
  if (snapshot.leftPanel === 'history') {
    return {
      title: 'История чатов',
      body: 'Выбери существующий чат, чтобы вернуть контекст, или закрой панель и продолжи в текущем потоке.',
      nextActions: ['Выбрать чат из history', 'Закрыть history panel', 'Вернуться к сообщению по текущей ноде'],
      shortcuts: [],
      tone: 'info',
    };
  }

  if (snapshot.leftPanel === 'models') {
    return buildModelDirectoryHint(snapshot);
  }

  if (snapshot.keyInventoryLoaded && !snapshot.hasAnyKeys) {
    return {
      title: 'Chat surface · setup first',
      body: 'Чат открыт, но ключей еще нет. Сначала открой phonebook и drawer API Keys. Один LLM key оживит cloud-модели, а Tavily key отдельно включает web/ search.',
      nextActions: ['Открыть phonebook', 'Открыть API Keys drawer', 'Вставить первый ключ'],
      shortcuts: [],
      tone: 'warning',
    };
  }

  return {
    title: 'Chat surface',
    body: 'Чат открыт. Можно написать задачу, открыть history или выбрать модель для маршрута ответа.',
    nextActions: ['Отправить сообщение', 'Открыть history', 'Открыть phonebook'],
    shortcuts: [],
    tone: 'info',
  };
}

function buildScannerHint(): MycoModeAHint {
  return {
    title: 'Scanner surface',
    body: 'Ты в scanner. Сначала подключи источник или выбери, что именно сканировать, затем верни найденное в рабочий контекст.',
    nextActions: ['Подключить источник', 'Запустить scan', 'Вернуть найденное в VETKA'],
    shortcuts: [],
    tone: 'action',
  };
}

function buildGroupHint(snapshot: MycoModeAFocusSnapshot): MycoModeAHint {
  if (!snapshot.hasActiveGroup) {
    return {
      title: 'Team setup',
      body: 'Ты собираешь командный чат. Команда набирается через Group Creator: кликни слот роли, затем выбери модель в левой phonebook panel, после этого создавай группу.',
      nextActions: ['Кликнуть role slot', 'Выбрать модель слева в phonebook', 'Создать группу'],
      shortcuts: [],
      tone: 'action',
    };
  }

  return {
    title: 'Group chat',
    body: 'Командный чат активен. Пиши в общий поток или адресно вызывай участников через @mention. Кнопка Team открывает настройки группы и снова ведет к левой phonebook panel для замены состава.',
    nextActions: ['Написать сообщение группе', 'Использовать @mention по роли', 'Открыть Team settings'],
    shortcuts: [],
    tone: 'action',
  };
}

function buildSearchHint(snapshot: MycoModeAFocusSnapshot): MycoModeAHint {
  // MARKER_163A.MODE_A.SEARCH.DISABLED_CONTEXT_REDIRECT.V1:
  // Disabled contexts must redirect user back to runnable VETKA/Web/File search modes.
  if (snapshot.disabledSearchAttempt) {
    return {
      title: `${snapshot.disabledSearchAttempt}/ недоступен`,
      body: 'Этот режим уже показан в UI, но пока не исполняется. Используй vetka/, web/ или file/.',
      nextActions: ['Вернуться в vetka/', 'Переключиться в web/', 'Переключиться в file/'],
      shortcuts: [],
      tone: 'warning',
    };
  }

  const bodies: Record<MycoModeAFocusSnapshot['searchContext'], string> = {
    vetka: 'Поиск настроен на индекс VETKA. Дальше можно искать код, документы и ноды внутри проекта.',
    web: 'Поиск настроен на интернет. Следующий шаг: открыть найденную страницу или сохранить ее в VETKA.',
    file: 'Поиск настроен на файловую систему. Если найдешь внешний файл, можно добавить его в индекс VETKA.',
    cloud: 'Cloud mode пока недоступен.',
    social: 'Social mode пока недоступен.',
  };

  const modeBodies: Record<MycoModeAFocusSnapshot['searchMode'], string> = {
    hybrid: 'HYB смешивает семантику и ключевые совпадения.',
    semantic: 'SEM полезен, когда важен смысл, а не точная строка.',
    keyword: 'KEY лучше для точных терминов, API-имен и явных фраз.',
    filename: 'FILE ищет по именам файлов и быстрым path-попаданиям.',
  };

  if (snapshot.searchContext === 'file') {
    return {
      title: 'file/ search',
      body: 'Поиск настроен на файловую систему пользователя вне VETKA. Найденный внешний файл можно открыть как артефакт и при необходимости добавить в индекс VETKA.',
      nextActions: ['Найти внешний файл', 'Открыть артефакт', 'Добавить внешний файл в VETKA'],
      shortcuts: [],
      tone: 'action',
    };
  }

  if (snapshot.searchContext === 'web') {
    if (snapshot.searchErrorCategory === 'auth') {
      return {
        title: 'web/ key auth error',
        body: 'web/ сейчас не проходит по ключу поиска. Похоже на invalid, expired или revoked key. Открой phonebook, затем API Keys drawer, замени Tavily key и повтори поиск. Пока можно продолжить через vetka/ или file/.',
        nextActions: ['Открыть phonebook', 'Заменить Tavily key', 'Вернуться в vetka/ или file/'],
        shortcuts: [],
        tone: 'warning',
      };
    }

    if (snapshot.searchErrorCategory === 'billing') {
      return {
        title: 'web/ quota or billing issue',
        body: 'Провайдер поиска ответил как quota или billing problem. Обычно помогает пополнить текущий key, заменить его на новый или временно уйти в vetka/ и file/. Если не хочешь вести отдельные ключи, можно позже перейти на VETKA subscription.',
        nextActions: ['Проверить баланс провайдера', 'Заменить Tavily key', 'Временно использовать vetka/ или file/'],
        shortcuts: [],
        tone: 'warning',
      };
    }

    if (snapshot.searchErrorCategory === 'rate_limit') {
      return {
        title: 'web/ rate limited',
        body: 'Текущий search key уперся в rate limit. Подожди, замени ключ или вернись в vetka/ и file/. Для длинной сессии полезно держать запасной search key.',
        nextActions: ['Повторить позже', 'Добавить запасной search key', 'Временно использовать vetka/ или file/'],
        shortcuts: [],
        tone: 'warning',
      };
    }

    if (snapshot.searchErrorCategory === 'timeout' || snapshot.searchErrorCategory === 'provider_down') {
      return {
        title: 'web/ provider not responding',
        body: 'Search provider сейчас не отвечает стабильно. Проверь сеть и сам сервис, затем повтори запрос. Пока не жди у пустого web/, а продолжай через vetka/ или file/.',
        nextActions: ['Повторить поиск позже', 'Проверить провайдера и сеть', 'Переключиться в vetka/ или file/'],
        shortcuts: [],
        tone: 'warning',
      };
    }

    if (
      snapshot.searchErrorCategory === 'missing_key'
      || snapshot.webProviderAvailable === false
      || !snapshot.hasSearchProviderKey
    ) {
      return {
        title: 'web/ needs Tavily key',
        body: 'В текущем runtime web/ работает через Tavily. Открой phonebook, затем API Keys drawer, и добавь Tavily key. Если ключа еще нет, найди Tavily API key в браузере и вернись сюда. Пока ключ не добавлен, используй vetka/ для project memory или file/ для локальной файловой системы. Если не хочешь заниматься несколькими ключами вручную, можно позже перейти на VETKA subscription.',
        nextActions: ['Открыть phonebook', 'Открыть API Keys drawer', 'Добавить Tavily key'],
        shortcuts: [],
        tone: 'warning',
      };
    }
  }

  return {
    title: `${snapshot.searchContext}/ search · ${snapshot.searchMode.toUpperCase()}`,
    body: `${bodies[snapshot.searchContext]} ${modeBodies[snapshot.searchMode]}`,
    nextActions: snapshot.searchContext === 'file'
      ? ['Найти файл', 'Открыть артефакт', 'Добавить внешний файл в VETKA']
      : snapshot.searchContext === 'web'
        ? ['Ввести запрос', 'Открыть результат', 'Сохранить страницу в VETKA']
        : ['Сменить источник поиска', 'Ввести запрос', 'Открыть результат'],
    shortcuts: [],
    tone: snapshot.searchContext === 'vetka' ? 'info' : 'action',
  };
}

function buildArtifactHint(snapshot: MycoModeAFocusSnapshot): MycoModeAHint {
  const contextAction = snapshot.isChatOpen ? 'Закрепить в контекст чата' : 'Сначала открыть чат, потом закрепить в контекст';
  const favoriteAction = snapshot.artifactInVetka ? 'Добавить в избранное через звезду' : 'Сначала добавить файл в VETKA';

  if (snapshot.artifactKind === 'web') {
    return {
      title: snapshot.artifactInVetka ? 'Web artifact' : 'External web artifact',
      body: snapshot.artifactInVetka
        ? 'Открыта веб-страница в artifact surface. Здесь можно читать live/html или markdown и сохранить страницу в VETKA через SAVE TO VETKA.'
        : 'Открыта веб-страница вне индексированного дерева. Сначала можно сохранить ее в VETKA через SAVE TO VETKA, затем вернуть в рабочий контекст.',
      nextActions: ['Просмотреть страницу', 'Нажать SAVE TO VETKA', contextAction],
      shortcuts: ['Cmd/Ctrl+S: сохранить'],
      tone: 'action',
    };
  }

  if (snapshot.artifactKind === 'video') {
    return {
      title: snapshot.artifactInVetka ? 'Video artifact' : 'External video artifact',
      body: snapshot.artifactInVetka
        ? 'Открыт видео-артефакт. Здесь доступны preview, timeline lanes и быстрый переход в Media Edit Mode.'
        : 'Открыт внешний видео-артефакт. Сначала его можно добавить в VETKA, но уже сейчас доступны preview и ориентир на Media Edit Mode.',
      nextActions: snapshot.artifactInVetka
        ? ['Проиграть видео', 'Проверить timeline lanes', 'Перейти в Media Edit Mode']
        : ['Добавить видео в VETKA', 'Проиграть видео', 'Перейти в Media Edit Mode'],
      shortcuts: ['Cmd/Ctrl+S: сохранить', 'Cmd/Ctrl+Z: undo'],
      tone: snapshot.artifactInVetka ? 'action' : 'warning',
    };
  }

  if (snapshot.artifactKind === 'audio') {
    return {
      title: snapshot.artifactInVetka ? 'Audio artifact' : 'External audio artifact',
      body: snapshot.artifactInVetka
        ? 'Открыт аудио-артефакт. Смотри waveform, сегменты и возвращай фрагменты обратно в рабочий контекст.'
        : 'Открыт внешний аудио-артефакт. Его стоит добавить в VETKA, но waveform и дальнейший проход по фрагментам уже подсказывают следующий монтажный шаг.',
      nextActions: snapshot.artifactInVetka
        ? ['Проиграть аудио', 'Проверить waveform', 'Вернуть контекст в чат']
        : ['Добавить аудио в VETKA', 'Проиграть аудио', 'Проверить waveform'],
      shortcuts: ['Cmd/Ctrl+S: сохранить', 'Cmd/Ctrl+Z: undo'],
      tone: snapshot.artifactInVetka ? 'action' : 'warning',
    };
  }

  if (snapshot.artifactLooksLikeCode) {
    return {
      title: snapshot.artifactInVetka ? 'Code artifact' : 'External code artifact',
      body: snapshot.isChatOpen
        ? `Открыт ${snapshot.artifactInVetka ? 'кодовый' : 'внешний кодовый'} артефакт. ${snapshot.artifactInVetka ? 'Звезда добавляет его в favorites,' : 'Сначала его лучше добавить в VETKA, затем уже работать как с внутренним файлом.'} Pin внизу закрепляет файл в контекст чата. Редактировать код прямо здесь можно, но это рискованный short path без полного review-loop.`
        : `Открыт ${snapshot.artifactInVetka ? 'кодовый' : 'внешний кодовый'} артефакт. ${snapshot.artifactInVetka ? 'Звезда добавляет его в favorites.' : 'Сначала его лучше добавить в VETKA.'} Если хочешь закрепить файл в контекст, сначала открой чат. Редактировать код прямо здесь можно, но это рискованный short path без полного review-loop.`,
      nextActions: [favoriteAction, contextAction, 'Редактировать код только если изменение точечное'],
      shortcuts: ['Cmd/Ctrl+S: сохранить', 'Cmd/Ctrl+Z: undo'],
      tone: 'warning',
    };
  }

  if (!snapshot.artifactInVetka) {
    // MARKER_163A.MODE_A.EXTERNAL_ARTIFACT.INGEST_HINT.V1:
    // External artifacts should prefer an ingest-oriented hint before any generic artifact guidance.
    return {
      title: 'External artifact',
      body: 'Файл открыт вне дерева VETKA. Сначала его можно добавить в индекс, затем работать с ним как с обычной нодой.',
      nextActions: ['Добавить файл в VETKA', 'Открыть связанный чат', 'Закрыть артефакт'],
      shortcuts: ['Cmd/Ctrl+S: сохранить', 'Cmd/Ctrl+Z: undo'],
      tone: 'warning',
    };
  }

  return {
    title: 'Artifact window',
    body: snapshot.isChatOpen
      ? 'Артефакт открыт в рабочей поверхности. Звезда добавляет его в favorites, редактирование безопасно для обычного документа, а pin внизу возвращает документ в контекст текущего чата.'
      : 'Артефакт открыт в рабочей поверхности. Звезда добавляет его в favorites, редактирование подходит для обычного документа. Чтобы вернуть документ в контекст чата, сначала открой чат.',
    nextActions: [favoriteAction, snapshot.artifactLooksLikeCode ? 'Редактировать осторожно' : 'Редактировать документ', contextAction],
    shortcuts: ['Cmd/Ctrl+S: сохранить', 'Cmd/Ctrl+Z: undo'],
    tone: 'action',
  };
}

export function buildMycoModeAHint(snapshot: MycoModeAFocusSnapshot): MycoModeAHint | null {
  if (!snapshot.chatInputEmpty) return null;
  if (!snapshot.searchQueryEmpty && !snapshot.isChatOpen && (snapshot.surface === 'tree' || snapshot.surface === 'search')) return null;

  switch (snapshot.surface) {
    case 'tree':
      return buildTreeHint(snapshot);
    case 'chat':
    case 'chat_history':
    case 'model_directory':
      return buildChatHint(snapshot);
    case 'search':
      return buildSearchHint(snapshot);
    case 'artifact':
      return buildArtifactHint(snapshot);
    case 'scanner':
      return buildScannerHint();
    case 'group_chat':
    case 'group_setup':
      return buildGroupHint(snapshot);
    case 'devpanel':
      return {
        title: 'DevPanel',
        body: 'Это системная поверхность. Используй ее для диагностики и pipeline controls, не как основной рабочий поток.',
        nextActions: ['Проверить pipeline activity', 'Закрыть DevPanel', 'Вернуться к дереву'],
        shortcuts: ['Cmd/Ctrl+Shift+D: toggle DevPanel'],
        tone: 'info',
      };
    case 'context_menu':
      return {
        title: 'Context menu',
        body: 'Контекстное меню уже привязано к выбранной ноде. Здесь безопаснее делать точечное действие, чем общий переход.',
        nextActions: ['Выбрать действие из меню', 'Закрыть меню', 'Вернуться к дереву'],
        shortcuts: [],
        tone: 'info',
      };
    default:
      return null;
  }
}
