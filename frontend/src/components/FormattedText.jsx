import React from 'react';

export function parseInline(text) {
  if (!text) return text;
  const parts = [];
  const regex = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*)/g;
  let lastIndex = 0;
  let match;
  let key = 0;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    const token = match[0];
    if (token.startsWith('`') && token.endsWith('`')) {
      parts.push(<code key={key++} className="md-inline-code">{token.slice(1, -1)}</code>);
    } else if (token.startsWith('**') && token.endsWith('**')) {
      parts.push(<strong key={key++} className="md-bold">{token.slice(2, -2)}</strong>);
    } else if (token.startsWith('*') && token.endsWith('*')) {
      parts.push(<em key={key++} className="md-italic">{token.slice(1, -1)}</em>);
    } else {
      parts.push(token);
    }
    lastIndex = regex.lastIndex;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts;
}

export default function FormattedText({ content }) {
  if (!content) return null;

  const lines = content.split('\n');
  const blocks = [];
  let inCodeBlock = false;
  let codeBuffer = [];
  let listBuffer = [];
  let listType = null;
  let blockKey = 0;

  const flushList = () => {
    if (listBuffer.length === 0) return;
    if (listType === 'ul') {
      blocks.push(
        <ul key={blockKey++} className="md-ul">
          {listBuffer.map((item, idx) => (
            <li key={idx} className="md-list-item">{parseInline(item)}</li>
          ))}
        </ul>
      );
    } else if (listType === 'ol') {
      blocks.push(
        <ol key={blockKey++} className="md-ol">
          {listBuffer.map((item, idx) => (
            <li key={idx} className="md-list-item">{parseInline(item)}</li>
          ))}
        </ol>
      );
    }
    listBuffer = [];
    listType = null;
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (line.trim().startsWith('```')) {
      flushList();
      if (!inCodeBlock) {
        inCodeBlock = true;
        codeBuffer = [];
      } else {
        inCodeBlock = false;
        blocks.push(
          <pre key={blockKey++} className="md-pre">
            <code className="md-code-block">{codeBuffer.join('\n')}</code>
          </pre>
        );
        codeBuffer = [];
      }
      continue;
    }

    if (inCodeBlock) {
      codeBuffer.push(line);
      continue;
    }

    const headingMatch = line.match(/^(#{1,4})\s+(.+)$/);
    if (headingMatch) {
      flushList();
      const level = headingMatch[1].length;
      const headingText = headingMatch[2];
      if (level <= 2) {
        blocks.push(<h3 key={blockKey++} className="md-h2">{parseInline(headingText)}</h3>);
      } else {
        blocks.push(<h4 key={blockKey++} className="md-h3">{parseInline(headingText)}</h4>);
      }
      continue;
    }

    const ulMatch = line.match(/^(\*|-)\s+(.+)$/);
    if (ulMatch) {
      if (listType !== 'ul') flushList();
      listType = 'ul';
      listBuffer.push(ulMatch[2]);
      continue;
    }

    const olMatch = line.match(/^(\d+)\.\s+(.+)$/);
    if (olMatch) {
      if (listType !== 'ol') flushList();
      listType = 'ol';
      listBuffer.push(olMatch[2]);
      continue;
    }

    flushList();
    if (line.trim() === '') {
      blocks.push(<div key={blockKey++} className="md-spacer" />);
    } else {
      blocks.push(<p key={blockKey++} className="md-p">{parseInline(line)}</p>);
    }
  }

  flushList();
  if (inCodeBlock && codeBuffer.length > 0) {
    blocks.push(
      <pre key={blockKey++} className="md-pre">
        <code className="md-code-block">{codeBuffer.join('\n')}</code>
      </pre>
    );
  }

  return <div className="formatted-markdown">{blocks}</div>;
}
