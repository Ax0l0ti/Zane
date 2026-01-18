import { marked } from 'marked';
import DOMPurify from 'dompurify';
import hljs from 'highlight.js';

// Configure marked with GitHub Flavored Markdown
marked.setOptions({
  gfm: true,
  breaks: true
});

// Custom renderer for code blocks with syntax highlighting
const renderer = new marked.Renderer();

renderer.code = function ({ text, lang }: { text: string; lang?: string }) {
  const language = lang && hljs.getLanguage(lang) ? lang : 'plaintext';
  const highlighted = hljs.highlight(text, { language }).value;
  return `<pre><code class="hljs language-${language}">${highlighted}</code></pre>`;
};

// Override inline code to not use highlighting
renderer.codespan = function ({ text }: { text: string }) {
  return `<code>${text}</code>`;
};

marked.use({ renderer });

/**
 * Parse markdown to sanitized HTML
 */
export function parseMarkdown(content: string): string {
  const rawHtml = marked.parse(content) as string;
  return DOMPurify.sanitize(rawHtml, {
    ADD_ATTR: ['target', 'rel'],
    ADD_TAGS: ['code', 'pre']
  });
}

/**
 * Check if content contains markdown syntax
 */
export function hasMarkdown(content: string): boolean {
  const markdownPatterns = [
    /^#{1,6}\s/m,      // Headers
    /\*\*.+\*\*/,      // Bold
    /\*.+\*/,          // Italic
    /`[^`]+`/,         // Inline code
    /```[\s\S]+```/,   // Code blocks
    /^\s*[-*+]\s/m,    // Unordered lists
    /^\s*\d+\.\s/m,    // Ordered lists
    /\[.+\]\(.+\)/,    // Links
    /^\|.+\|$/m        // Tables
  ];

  return markdownPatterns.some((pattern) => pattern.test(content));
}
