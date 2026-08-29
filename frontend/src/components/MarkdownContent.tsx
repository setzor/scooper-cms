import React from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { atomDark, atomLight } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { useThemeContext } from '../contexts/ThemeContext';
import { cn } from '../utils/cn';

interface MarkdownContentProps {
  content: string;
  className?: string;
}

export function MarkdownContent({ content, className }: MarkdownContentProps) {
  const { theme } = useThemeContext();

  return (
    <ReactMarkdown
      className={cn('prose max-w-none', className)}
      components={{
        code({ node, inline, className, children, ...props }) {
          const match = /language-(\w+)/.exec(className || '');
          return !inline && match ? (
            <SyntaxHighlighter
              style={theme === 'dark' ? atomDark : atomLight}
              language={match[1]}
              PreTag="div"
              {...props}
            >
              {String(children).replace(/\n$/, '')}
            </SyntaxHighlighter>
          ) : (
            <code className={className} {...props}>
              {children}
            </code>
          );
        },
        img({ node, ...props }) {
          return (
            <img
              {...props}
              className="rounded-lg my-4 w-full max-w-full h-auto"
              alt={props.alt || ''}
            />
          );
        },
        blockquote({ node, ...props }) {
          return (
            <blockquote
              {...props}
              className="border-l-4 border-primary-500 pl-4 py-2 my-4 bg-gray-50 dark:bg-gray-800 rounded-r-lg"
            />
          );
        },
        a({ node, ...props }) {
          return (
            <a
              {...props}
              className="text-primary-600 dark:text-primary-400 hover:underline"
            />
          );
        },
      }}
    >
      {content}
    </ReactMarkdown>
  );
}
