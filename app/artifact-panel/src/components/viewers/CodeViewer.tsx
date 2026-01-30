import CodeMirror from '@uiw/react-codemirror';
import { javascript } from '@codemirror/lang-javascript';
import { python } from '@codemirror/lang-python';
import { oneDark } from '@codemirror/theme-one-dark';
import { search, searchKeymap } from '@codemirror/search'; // ✅ TASK 4: Search
import { keymap } from '@codemirror/view';
import { getLanguage } from '../../utils/fileTypes';

interface Props {
  content: string;
  filename: string;
  readOnly?: boolean;
  onChange?: (value: string) => void;
}

export function CodeViewer({ content, filename, readOnly = true, onChange }: Props) {
  const lang = getLanguage(filename);
  
  const getExtension = () => {
    if (lang === 'javascript' || lang === 'typescript') return javascript({ jsx: true, typescript: lang === 'typescript' });
    if (lang === 'python') return python();
    return [];
  };

  return (
    <div className="h-full flex flex-col bg-vetka-bg">
      {/* ✅ TASK 4: Search hint */}
      <div className="text-xs text-vetka-muted px-2 py-1 border-b border-vetka-border">
        Press Ctrl+F to search in code (highlight • Enter next • Esc close)
      </div>
      
      <div className="flex-1 overflow-auto">
        <CodeMirror
          value={content}
          theme={oneDark}
          extensions={[
            getExtension(),
            search(), // ✅ Enable search
            keymap.of(searchKeymap), // ✅ Keyboard shortcuts
          ]}
          readOnly={readOnly}
          onChange={onChange}
          basicSetup={{
            lineNumbers: true,
            highlightActiveLineGutter: true,
            highlightActiveLine: true,
            foldGutter: true,
          }}
          className="min-h-full text-sm"
        />
      </div>
    </div>
  );
}
