/**
 * CodeViewer - Syntax highlighted code editor/viewer.
 * Uses CodeMirror with oneDark theme and language extensions.
 *
 * @status active
 * @phase 96
 * @depends @uiw/react-codemirror, @codemirror/lang-javascript, @codemirror/lang-python, @codemirror/theme-one-dark, @codemirror/search
 * @used_by ArtifactPanel, CompoundMessage
 */

import CodeMirror from '@uiw/react-codemirror';
import { javascript } from '@codemirror/lang-javascript';
import { python } from '@codemirror/lang-python';
import { oneDark } from '@codemirror/theme-one-dark';
import { search, searchKeymap } from '@codemirror/search';
import { keymap } from '@codemirror/view';
import { getLanguage } from '../utils/fileTypes';

interface Props {
  content: string;
  filename: string;
  readOnly?: boolean;
  onChange?: (value: string) => void;
}

export function CodeViewer({ content, filename, readOnly = true, onChange }: Props) {
  const lang = getLanguage(filename);

  const getExtension = () => {
    if (lang === 'javascript' || lang === 'typescript') {
      return javascript({ jsx: true, typescript: lang === 'typescript' });
    }
    if (lang === 'python') return python();
    return [];
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: '#0a0a0a' }}>
      <div style={{ flex: 1, overflow: 'auto' }}>
        <CodeMirror
          value={content}
          theme={oneDark}
          extensions={[
            getExtension(),
            search(),
            keymap.of(searchKeymap),
          ]}
          readOnly={readOnly}
          onChange={onChange}
          basicSetup={{
            lineNumbers: true,
            highlightActiveLineGutter: true,
            highlightActiveLine: true,
            foldGutter: true,
          }}
          style={{ minHeight: '100%', fontSize: 13 }}
        />
      </div>
    </div>
  );
}
