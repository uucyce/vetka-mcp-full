import { useEditor, EditorContent } from '@tiptap/react';
import { useEffect } from 'react';
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import { Bold, Italic, Code, List, ListOrdered, Heading1, Heading2, Quote, FileCode, RotateCcw, RotateCw } from 'lucide-react';

interface Props {
  content: string;
  readOnly?: boolean;
  onChange?: (html: string) => void;
}

export function RichTextEditor({ content, readOnly = false, onChange }: Props) {
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: { levels: [1, 2, 3] }
      }),
      Placeholder.configure({ placeholder: 'Start typing...' }),
    ],
    content,
    editable: !readOnly,
    onUpdate: ({ editor }) => onChange?.(editor.getHTML()),
    editorProps: {
      attributes: {
        class: 'prose prose-invert max-w-none p-4 focus:outline-none min-h-full text-vetka-text',
      },
    },
  });

  // Cleanup editor on unmount (prevent memory leaks)
  useEffect(() => {
    return () => {
      if (editor) {
        editor.destroy();
      }
    };
  }, [editor]);

  if (!editor) return null;

  const Btn = ({ onClick, active, disabled, children, title }: {
    onClick: () => void;
    active?: boolean;
    disabled?: boolean;
    children: React.ReactNode;
    title: string;
  }) => (
    <button
      onClick={onClick}
      title={title}
      disabled={disabled}
      className={`p-1.5 rounded transition-colors ${
        disabled
          ? 'opacity-30 cursor-not-allowed'
          : active
            ? 'bg-vetka-border text-white'
            : 'text-vetka-muted hover:bg-vetka-border hover:text-white'
      }`}
    >
      {children}
    </button>
  );

  return (
    <div className="relative h-full bg-vetka-bg text-vetka-text flex flex-col">
      {!readOnly && (
        <div className="flex items-center gap-1 p-2 border-b border-vetka-border bg-vetka-surface flex-wrap">
          <Btn
            onClick={() => editor.chain().focus().undo().run()}
            disabled={!editor.can().undo()}
            title="Undo (Ctrl+Z)"
          >
            <RotateCcw size={16} />
          </Btn>
          <Btn
            onClick={() => editor.chain().focus().redo().run()}
            disabled={!editor.can().redo()}
            title="Redo (Ctrl+Shift+Z)"
          >
            <RotateCw size={16} />
          </Btn>
          <div className="w-px h-4 bg-vetka-border mx-1" />
          <Btn onClick={() => editor.chain().focus().toggleBold().run()} active={editor.isActive('bold')} title="Bold">
            <Bold size={16} />
          </Btn>
          <Btn onClick={() => editor.chain().focus().toggleItalic().run()} active={editor.isActive('italic')} title="Italic">
            <Italic size={16} />
          </Btn>
          <Btn onClick={() => editor.chain().focus().toggleCode().run()} active={editor.isActive('code')} title="Code">
            <Code size={16} />
          </Btn>
          <Btn onClick={() => editor.chain().focus().toggleBulletList().run()} active={editor.isActive('bulletList')} title="List">
            <List size={16} />
          </Btn>
          <Btn onClick={() => editor.chain().focus().toggleOrderedList().run()} active={editor.isActive('orderedList')} title="Numbered">
            <ListOrdered size={16} />
          </Btn>
          <div className="w-px h-4 bg-vetka-border mx-1" />
          <Btn onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()} active={editor.isActive('heading', { level: 1 })} title="H1">
            <Heading1 size={16} />
          </Btn>
          <Btn onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()} active={editor.isActive('heading', { level: 2 })} title="H2">
            <Heading2 size={16} />
          </Btn>
          <Btn onClick={() => editor.chain().focus().toggleBlockquote().run()} active={editor.isActive('blockquote')} title="Quote">
            <Quote size={16} />
          </Btn>
          <Btn onClick={() => editor.chain().focus().toggleCodeBlock().run()} active={editor.isActive('codeBlock')} title="Code Block">
            <FileCode size={16} />
          </Btn>
        </div>
      )}

      <EditorContent editor={editor} className="flex-1 overflow-auto" />
    </div>
  );
}
