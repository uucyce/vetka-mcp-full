# Анализ механизмов вызова артефактов и двойных кликов - Фаза 118

## Обзор задачи
Цель: заменить вызов артефакта через иконку на двойной клик по файлу, а также добавить приближение камеры к ветке по двойному клику.

## 🔍 Текущий механизм вызова артефактов (НАЙДЕН)

### 1. Основные кнопки-иконки (ChestIcon)

**Локация:** [`client/src/App.tsx`](client/src/App.tsx:617)

```typescript
// MARKER_ARTIFACT_ICON_1: Главная кнопка артефакта в App.tsx
{/* Artifact/Chest button */}
<button
  onClick={() => setIsArtifactOpen(!isArtifactOpen)}
  disabled={!selectedNode}
  // ... стили ...
  title={selectedNode ? 'View artifact' : 'Select a file first'}
>
  <ChestIcon isOpen={isArtifactOpen} />
</button>
```

**Место:** Строки 617-650 и 686-712 (два экземпляра кнопки)
**Поведение:** Открывает [`ArtifactWindow`](client/src/components/artifact/ArtifactWindow.tsx) для выбранного узла

### 2. Вызов артефакта из поиска

**Локация:** [`client/src/components/search/UnifiedSearchBar.tsx`](client/src/components/search/UnifiedSearchBar.tsx:1087)

```typescript
// MARKER_ARTIFACT_ICON_2: Кнопка артефакта в результатах поиска
{onOpenArtifact && (
  <button
    onClick={(e) => handleArtifact(e, result)}
    style={{ ...styles.iconButton, color: '#444' }}
    // ...
  />
)}
```

**Место:** Строка 1087-1090
**Поведение:** Открывает артефакт для результата поиска

### 3. Вызов артефакта в чате

**Локация:** [`client/src/components/chat/MessageBubble.tsx`](client/src/components/chat/MessageBubble.tsx:366)

```typescript
// MARKER_ARTIFACT_ICON_3: Кнопка артефакта в сообщениях чата
<button
  onClick={() => onOpenArtifact?.(message.id, message.content || '', modelName)}
  // ... стили ...
/>
```

**Место:** Строка 366-368

## 🎯 Текущие обработчики кликов в FileCard (НАЙДЕН)

### Основной обработчик кликов

**Локация:** [`client/src/components/canvas/FileCard.tsx`](client/src/components/canvas/FileCard.tsx:894)

```typescript
// MARKER_CLICK_HANDLER: Обработчик кликов в FileCard
const handleClick = useCallback(
  (e: ThreeEvent<MouseEvent>) => {
    // Ctrl/Cmd+Click для драгa
    if (e.ctrlKey || e.metaKey) return;
    
    e.stopPropagation();
    
    // Shift+Click = Smart Pin
    if (e.shiftKey) {
      pinNodeSmart(id);
      return;
    }
    
    // Chat nodes
    if (type === 'chat') {
      window.dispatchEvent(new CustomEvent('vetka-open-chat', {
        detail: { chatId, fileName: name, filePath: path }
      }));
      return;
    }
    
    // Artifact nodes  
    if (type === 'artifact' && artifactId) {
      window.dispatchEvent(new CustomEvent('vetka-open-artifact', {
        detail: { artifactId, fileName: name, filePath: path, status: artifactStatus, artifactType }
      }));
      return;
    }
    
    // Normal click = Select
    onClick?.();
  },
  [onClick, id, pinNodeSmart, type, metadata, name, path, artifactId, artifactStatus, artifactType]
);
```

**Место:** Строки 894-948
**Текущее поведение:** 
- Обычный клик = выбор узла
- Shift+Click = пинирование
- Ctrl/Cmd+Click = начало драга 
- **❌ НЕТ ОБРАБОТКИ ДВОЙНОГО КЛИКА**

## 📹 Система управления камерой (НАЙДЕН)

### CameraController - основной компонент

**Локация:** [`client/src/components/canvas/CameraController.tsx`](client/src/components/canvas/CameraController.tsx:32)

```typescript
// MARKER_CAMERA_CONTROLLER: Главный контроллер камеры
export function CameraController() {
  const { camera } = useThree();
  const cameraCommand = useStore((state) => state.cameraCommand);
  const setCameraCommand = useStore((state) => state.setCameraCommand);
  
  // Обработка команд камеры
  useEffect(() => {
    if (!cameraCommand) return;
    
    const nodeEntry = findNode(cameraCommand.target);
    if (!nodeEntry) return;
    
    const finalDistance = cameraCommand.zoom === 'close' ? 20
                        : cameraCommand.zoom === 'medium' ? 30 : 45;
                        
    // Анимация движения камеры...                    
  }, [cameraCommand, nodes, selectNode, highlightNode, setCameraCommand]);
}
```

**Место:** Весь файл, ключевые строки 32-197
**Функциональность:**
- Анимированное плавное движение камеры
- Три уровня зума: close (20), medium (30), far (45)
- Интеграция с OrbitControls

### Команды камеры через Store

**Локация:** [`client/src/App.tsx`](client/src/App.tsx:252) и другие

```typescript
// MARKER_CAMERA_COMMANDS: Использование команд камеры
const setCameraCommand = useStore((state) => state.setCameraCommand);

// Пример вызова
setCameraCommand({ target: result.path, zoom: 'close', highlight: true });
```

**Типы зума:** 'close' | 'medium' | 'far'

## 📋 Компоненты артефактов (ПРОАНАЛИЗИРОВАН)

### ArtifactWindow - обёртка

**Локация:** [`client/src/components/artifact/ArtifactWindow.tsx`](client/src/components/artifact/ArtifactWindow.tsx:48)
- Floating window для отображения артефактов
- Интеграция с ApprovalLevel для L1/L2/L3

### ArtifactPanel - основной компонент

**Локация:** [`client/src/components/artifact/ArtifactPanel.tsx`](client/src/components/artifact/ArtifactPanel.tsx:74)
- Отображение файлов и raw контента
- Поддержка редактирования (L2 mode)
- Lazy loading viewers для разных типов файлов

### Viewers (просмотрщики)

1. **CodeViewer:** [`client/src/components/artifact/viewers/CodeViewer.tsx`](client/src/components/artifact/viewers/CodeViewer.tsx:1)
2. **ImageViewer:** [`client/src/components/artifact/viewers/ImageViewer.tsx`](client/src/components/artifact/viewers/ImageViewer.tsx:1)
3. **MarkdownViewer:** [`client/src/components/artifact/viewers/MarkdownViewer.tsx`](client/src/components/artifact/viewers/MarkdownViewer.tsx:1)

## 🎯 Предлагаемое решение

### 1. Добавить обработку двойного клика в FileCard

```typescript
// НОВЫЙ КОД: Добавить в FileCard.tsx
const [clickCount, setClickCount] = useState(0);
const clickTimer = useRef<NodeJS.Timeout>();

const handleDoubleClick = useCallback((e: ThreeEvent<MouseEvent>) => {
  if (type === 'file') {
    // Двойной клик на файл = открыть артефакт
    // Аналогично текущей логике кнопки ChestIcon
  } else if (type === 'folder') {
    // Двойной клик на папку = приблизить камеру
    setCameraCommand({
      target: path,
      zoom: 'medium',
      highlight: true
    });
  }
}, [type, path, setCameraCommand]);
```

### 2. Места для изменений

**Основное место:** [`client/src/components/canvas/FileCard.tsx`](client/src/components/canvas/FileCard.tsx:894)
- Добавить логику отслеживания двойного клика
- Интегрировать с существующими обработчиками

**Дополнительно:** [`client/src/App.tsx`](client/src/App.tsx:617)
- Возможно, сохранить кнопку как fallback или убрать

### 3. Интеграция с камерой

Использовать существующую систему [`setCameraCommand`](client/src/components/canvas/CameraController.tsx:34):
- Для файлов: открыть артефакт (новое поведение)
- Для папок/веток: `zoom: 'medium'` для комфортного обзора

## 📝 Ключевые выводы

1. **✅ Механизм артефактов хорошо изучен** - есть 3 основных места вызова
2. **❌ Двойные клики НЕ реализованы** - нужно добавить с нуля  
3. **✅ Система камеры готова** - [`CameraController`](client/src/components/canvas/CameraController.tsx) поддерживает нужную функциональность
4. **🎯 Основная точка изменений** - [`FileCard.tsx`](client/src/components/canvas/FileCard.tsx) handleClick

## 🔧 Следующие шаги

1. Реализовать double-click detection в FileCard
2. Добавить условия для файлов vs папок
3. Интегрировать с существующей системой артефактов
4. Настроить камеру для веток (zoom: 'medium')
5. Протестировать интеграцию

---
*Отчет создан: $(date)*
*Анализ выполнен для фазы 118*