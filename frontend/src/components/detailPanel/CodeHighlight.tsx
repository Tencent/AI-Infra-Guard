import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { tomorrow } from 'react-syntax-highlighter/dist/esm/styles/prism';

const CodeHighlight: React.FC<{ children: string }> = ({ children }) => {
  // Handle leading whitespace by removing tabs and spaces at the start
  const cleanContent = (content: string) => {
    const lines = content.split('\n');
    const cleanedLines = lines.map(line => line.replace(/^[\t\s]+/, ''));
    return cleanedLines.join('\n');
  };

  const codeComponent = ({ children, className }: { children: React.ReactNode; className?: string }) => {
    const isInline = !className;
    if (isInline) {
      return (
        <code className='bg-gray-100 text-gray-800 px-1 py-0.5 rounded text-sm font-mono'>
          {children}
        </code>
      );
    }
    // Extract the language identifier
    const match = /language-(\w+)/.exec(className || '');
    const language = match ? match[1] : '';
    let highlightLanguage = language;
    if (
      language === 'shell' ||
      language === 'bash' ||
      language === 'sh' ||
      language === 'zsh'
    ) {
      highlightLanguage = 'bash';
    } else if (language === 'ts') {
      highlightLanguage = 'typescript';
    } else if (language === 'js') {
      highlightLanguage = 'javascript';
    }
    return (
      <div className='not-prose'>
        <SyntaxHighlighter
          language={highlightLanguage}
          style={tomorrow}
          customStyle={{
            margin: 0,
            borderRadius: '0.5rem',
            fontSize: '0.875rem',
            lineHeight: '1.5',
          }}
          showLineNumbers={true}
          wrapLines={true}
        >
          {String(children).replace(/\n$/, '')}
        </SyntaxHighlighter>
      </div>
    );
  };

  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        code: codeComponent,
        p: ({ children }) => (
          <p className="mb-3 leading-relaxed">{children}</p>
        ),
        h1: ({ children }) => (
          <h1 className="text-lg font-semibold mb-3 mt-4">{children}</h1>
        ),
        h2: ({ children }) => (
          <h2 className="text-base font-semibold mb-2 mt-3">{children}</h2>
        ),
        h3: ({ children }) => (
          <h3 className="text-sm font-semibold mb-2 mt-3">{children}</h3>
        ),
        ul: ({ children }) => (
          <ul className="mb-3 space-y-1">{children}</ul>
        ),
        ol: ({ children }) => (
          <ol className="mb-3 space-y-1">{children}</ol>
        ),
        li: ({ children }) => (
          <li className="ml-4 leading-relaxed">{children}</li>
        ),
        blockquote: ({ children }) => (
          <blockquote className="border-l-4 border-gray-300 pl-4 py-2 mb-3 italic text-gray-600">
            {children}
          </blockquote>
        ),
      }}
    >
      {cleanContent(children)}
    </ReactMarkdown>
  );
};

export default CodeHighlight; 