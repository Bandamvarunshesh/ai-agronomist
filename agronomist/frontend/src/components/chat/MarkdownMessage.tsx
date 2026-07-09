import type { ReactNode } from "react";

type MarkdownMessageProps = {
  content: string;
};

type Block =
  | { type: "heading"; level: 1 | 2 | 3; text: string }
  | { type: "paragraph"; text: string }
  | { type: "list"; ordered: boolean; items: string[] }
  | { type: "code"; code: string; language: string | null };

const INLINE_PATTERN =
  /(\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)|`([^`]+)`|\*\*([^*]+)\*\*|\*([^*]+)\*)/g;

function renderInline(text: string, keyPrefix: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  let lastIndex = 0;
  let matchIndex = 0;

  for (const match of text.matchAll(INLINE_PATTERN)) {
    const matchedText = match[0];
    const matchStart = match.index ?? 0;
    const matchEnd = matchStart + matchedText.length;

    if (matchStart > lastIndex) {
      nodes.push(text.slice(lastIndex, matchStart));
    }

    if (match[2] && match[3]) {
      nodes.push(
        <a
          className="markdown-link"
          href={match[3]}
          key={`${keyPrefix}-link-${matchIndex}`}
          rel="noreferrer"
          target="_blank"
        >
          {match[2]}
        </a>,
      );
    } else if (match[4]) {
      nodes.push(
        <code className="markdown-inline-code" key={`${keyPrefix}-code-${matchIndex}`}>
          {match[4]}
        </code>,
      );
    } else if (match[5]) {
      nodes.push(
        <strong key={`${keyPrefix}-strong-${matchIndex}`}>{match[5]}</strong>,
      );
    } else if (match[6]) {
      nodes.push(<em key={`${keyPrefix}-em-${matchIndex}`}>{match[6]}</em>);
    }

    lastIndex = matchEnd;
    matchIndex += 1;
  }

  if (lastIndex < text.length) {
    nodes.push(text.slice(lastIndex));
  }

  return nodes.length ? nodes : [text];
}

function parseBlocks(content: string): Block[] {
  const lines = content.replace(/\r\n/g, "\n").split("\n");
  const blocks: Block[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    const trimmed = line.trim();

    if (!trimmed) {
      index += 1;
      continue;
    }

    const codeFenceMatch = trimmed.match(/^```([a-zA-Z0-9_-]+)?$/);
    if (codeFenceMatch) {
      index += 1;
      const codeLines: string[] = [];
      while (index < lines.length && !lines[index].trim().startsWith("```")) {
        codeLines.push(lines[index]);
        index += 1;
      }
      if (index < lines.length) {
        index += 1;
      }
      blocks.push({
        type: "code",
        code: codeLines.join("\n"),
        language: codeFenceMatch[1] || null,
      });
      continue;
    }

    const headingMatch = line.match(/^(#{1,3})\s+(.+)$/);
    if (headingMatch) {
      blocks.push({
        type: "heading",
        level: headingMatch[1].length as 1 | 2 | 3,
        text: headingMatch[2].trim(),
      });
      index += 1;
      continue;
    }

    const unorderedMatch = line.match(/^[-*]\s+(.+)$/);
    const orderedMatch = line.match(/^\d+\.\s+(.+)$/);
    if (unorderedMatch || orderedMatch) {
      const ordered = Boolean(orderedMatch);
      const items: string[] = [];
      while (index < lines.length) {
        const currentLine = lines[index];
        const nextMatch = ordered
          ? currentLine.match(/^\d+\.\s+(.+)$/)
          : currentLine.match(/^[-*]\s+(.+)$/);
        if (!nextMatch) {
          break;
        }
        items.push(nextMatch[1].trim());
        index += 1;
      }
      blocks.push({ type: "list", ordered, items });
      continue;
    }

    const paragraphLines = [trimmed];
    index += 1;
    while (index < lines.length) {
      const nextLine = lines[index];
      const nextTrimmed = nextLine.trim();
      if (
        !nextTrimmed ||
        nextTrimmed.startsWith("```") ||
        /^(#{1,3})\s+/.test(nextLine) ||
        /^[-*]\s+/.test(nextLine) ||
        /^\d+\.\s+/.test(nextLine)
      ) {
        break;
      }
      paragraphLines.push(nextTrimmed);
      index += 1;
    }
    blocks.push({ type: "paragraph", text: paragraphLines.join(" ") });
  }

  return blocks;
}

export function MarkdownMessage({ content }: MarkdownMessageProps) {
  const blocks = parseBlocks(content);

  return (
    <div className="markdown-message">
      {blocks.map((block, index) => {
        const key = `block-${index}`;

        if (block.type === "heading") {
          if (block.level === 1) {
            return <h1 key={key}>{renderInline(block.text, key)}</h1>;
          }
          if (block.level === 2) {
            return <h2 key={key}>{renderInline(block.text, key)}</h2>;
          }
          return <h3 key={key}>{renderInline(block.text, key)}</h3>;
        }

        if (block.type === "code") {
          return (
            <pre className="markdown-code-block" key={key}>
              <code data-language={block.language || undefined}>{block.code}</code>
            </pre>
          );
        }

        if (block.type === "list") {
          const ListTag = block.ordered ? "ol" : "ul";
          return (
            <ListTag className="markdown-list" key={key}>
              {block.items.map((item, itemIndex) => (
                <li key={`${key}-${itemIndex}`}>{renderInline(item, `${key}-${itemIndex}`)}</li>
              ))}
            </ListTag>
          );
        }

        return <p key={key}>{renderInline(block.text, key)}</p>;
      })}
    </div>
  );
}
