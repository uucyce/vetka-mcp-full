# PHASE 56.5: Quick Start Integration Checklist

**⏱️ Estimated Time:** 30 minutes
**🎯 Goal:** Get the unified panel working in your app

---

## 🚀 Step 1: Install Dependencies (5 min)

```bash
cd client
npm install
# Should add: framer-motion, gsap, react-hotkeys-hook, immer
```

✅ Verify:
```bash
npm list framer-motion
npm run build  # Should have no TypeScript errors
```

---

## 📂 Step 2: Check File Structure (2 min)

All files created ✅:

```
client/src/
├── types/
│   └── treeNodes.ts ✅
├── store/
│   ├── chatTreeStore.ts ✅
│   └── roleStore.ts ✅
├── hooks/
│   └── useModelRegistry.ts ✅
└── components/
    ├── canvas/
    │   ├── ChatNodeMesh.tsx ✅
    │   ├── ArtifactNodeMesh.tsx ✅
    │   └── HostessMemoryView.tsx ✅
    └── panels/
        ├── UnifiedPanel.tsx ✅
        ├── PhonebookTab.tsx ✅
        ├── HistoryTab.tsx ✅
        └── RoleEditor.tsx ✅

src/
└── memory/
    └── hostess_memory.py ✅
```

---

## 🔌 Step 3: Add UnifiedPanel to App (3 min)

### Find your App.tsx:

```tsx
import { UnifiedPanel } from './components/panels/UnifiedPanel';

export function App() {
  return (
    <div>
      {/* Your existing components */}

      {/* ADD THIS LINE: */}
      <UnifiedPanel />
    </div>
  );
}
```

✅ Test: `npm run dev` → Should see 📞 button in bottom-right

---

## 🎨 Step 4: Integrate 3D Nodes (10 min)

### Find your 3D scene component (likely Canvas in your main view):

```tsx
import { ChatNodeMesh } from './components/canvas/ChatNodeMesh';
import { ArtifactNodeMesh } from './components/canvas/ArtifactNodeMesh';
import { useChatTreeStore } from './store/chatTreeStore';

export function YourScene() {
  const chatNodes = useChatTreeStore(s => Object.values(s.chatNodes));
  const artifactNodes = useChatTreeStore(s => Object.values(s.artifactNodes));

  // Your existing file node rendering...

  return (
    <Canvas>
      {/* Existing file nodes */}

      {/* ADD THESE: */}
      {chatNodes.map(chat => {
        // Use your layout algorithm to calculate position
        const position = calculateNodePosition(chat.id);
        return (
          <ChatNodeMesh
            key={chat.id}
            nodeId={chat.id}
            position={position}
            onSelect={(id) => console.log('Selected:', id)}
          />
        );
      })}

      {artifactNodes.map(artifact => {
        const position = calculateNodePosition(artifact.id);
        return (
          <ArtifactNodeMesh
            key={artifact.id}
            nodeId={artifact.id}
            position={position}
            onSelect={(id) => console.log('Selected:', id)}
          />
        );
      })}
    </Canvas>
  );
}
```

✅ Test: Click 📞 → Create chat → Should see node appear in tree

---

## ⚡ Step 5: Test Frontend (5 min)

In your browser:

1. **Click** 📞 button (or press `Ctrl+P`)
2. **Panel appears** from right with smooth animation
3. **Select file** in tree (should show "Context from: filename.ts")
4. **Click** ➕ to create custom role
5. **Fill** role details:
   - Role ID: `@expert`
   - Display Name: `Expert Advisor`
   - System Prompt: (any text)
6. **Click** "Create Role" → Role appears in list
7. **Click** role → Adds to selected agents
8. **Click** "Start Chat" → (Should work if socket connected)

✅ All working? **Frontend is ready!**

---

## 🔧 Step 6: Test Backend Socket Handlers (5 min)

In Node.js console (browser DevTools):

```javascript
// Check if socket is connected
// Go to Console tab:
window.location.hostname + ':5001'  // Should show API URL

// Watch for socket events:
// Go to Network → WS tab
// You should see "socketio" connection
```

✅ Socket connected?

---

## 🧪 Step 7: Verify Store Persistence (3 min)

In browser console:

```javascript
// Check localStorage
localStorage.getItem('vetka-custom-roles')
// Should show JSON string of your created roles

// Clear if needed:
// localStorage.removeItem('vetka-custom-roles')
```

✅ Roles persist after page reload?

---

## 📊 Quick Verification Checklist

- [ ] Dependencies installed (`npm list framer-motion`)
- [ ] No TypeScript errors (`npm run build`)
- [ ] 📞 FAB button visible
- [ ] `Ctrl+P` opens/closes panel
- [ ] Panel slides in smoothly
- [ ] Can click Phonebook tab
- [ ] Can click History tab
- [ ] Can create custom role
- [ ] Role saves to localStorage
- [ ] Can select agents
- [ ] "Start Chat" button enabled with agents selected
- [ ] Chat node appears in 3D tree (if integrated)
- [ ] Socket connection shows in DevTools (Network → WS)

**All checked? ✅ Phase 56.5 is working!**

---

## 🐛 Troubleshooting

### Panel doesn't appear

```bash
# 1. Check console for errors
# DevTools → Console → Look for red errors

# 2. Verify file path
grep -r "UnifiedPanel" client/src/App.tsx

# 3. Check import
# Should be: import { UnifiedPanel } from './components/panels/UnifiedPanel'
```

### Button visible but doesn't open

```javascript
// In console, check if Framer Motion loaded:
window.MotionConfig // Should exist

// Check for class conflicts:
document.querySelector('[aria-label="Open Phonebook"]') // Should find it
```

### Chat node doesn't appear in tree

```javascript
// Check store has nodes:
// Open Redux/Store DevTools if available
// Or in console:
// (assuming you export store)
useChatTreeStore.getState().chatNodes
```

### Socket events not firing

```bash
# 1. Check backend is running
curl http://localhost:5001/api/health

# 2. Check WebSocket connection
# DevTools → Network → Filter "WS"
# Should see socketio connection

# 3. Check event listeners
grep "chat_node_created" client/src/hooks/useSocket.ts
```

---

## 📚 Reference

- **Full Guide:** `docs/PHASE_56_5_IMPLEMENTATION_GUIDE.md`
- **Component Docs:** Comment headers in component files
- **Type Definitions:** `client/src/types/treeNodes.ts`

---

## 🎉 Next Steps

Once Phase 56.5 is working:

1. **Phase 56.6:** Integrate artifact generation
2. **Phase 56.7:** Stream messages in real-time
3. **Phase 56.8:** Export chat history

---

## 📞 Need Help?

1. Check console for errors: `F12 → Console tab`
2. Verify socket connection: `F12 → Network → WS tab`
3. Review implementation guide: `docs/PHASE_56_5_IMPLEMENTATION_GUIDE.md`
4. Check backend logs: `python main.py` output

---

**Status:** ✅ Ready to integrate
**Time:** ~30 minutes
**Difficulty:** 🟢 Easy

Let's go! 🚀
