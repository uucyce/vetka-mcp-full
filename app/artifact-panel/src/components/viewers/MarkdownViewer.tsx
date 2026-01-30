import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';

interface Props {
  content: string;
}

export function MarkdownViewer({ content }: Props) {
  return (
    <div className="h-full overflow-auto bg-vetka-bg p-6">
      <div className="prose prose-invert max-w-none text-vetka-text">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          rehypePlugins={[rehypeKatex]}
          components={{
            h1: ({ ...props }) => <h1 className="text-3xl font-bold text-white mb-4" {...props} />,
            h2: ({ ...props }) => <h2 className="text-2xl font-bold text-white mb-3" {...props} />,
            h3: ({ ...props }) => <h3 className="text-xl font-bold text-white mb-2" {...props} />,
            p: ({ ...props }) => <p className="mb-3 leading-relaxed" {...props} />,
            code: ({ inline, ...props }: any) => inline 
              ? <code className="bg-vetka-surface px-1.5 py-0.5 rounded text-sm text-vetka-text" {...props} />
              : <code className="bg-vetka-surface block p-3 rounded-lg overflow-auto text-sm my-2" {...props} />,
            blockquote: ({ ...props }) => <blockquote className="border-l-4 border-vetka-border pl-4 italic text-vetka-muted my-4" {...props} />,
            a: ({ ...props }) => <a className="text-blue-400 hover:underline" {...props} />,
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
    </div>
  );
}
