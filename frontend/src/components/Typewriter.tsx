import React, { useState, useEffect, useRef } from 'react';

interface TypewriterProps {
  content: string; // HTML string content
  speed?: number;
  onComplete?: () => void;
  containerRef?: React.RefObject<HTMLDivElement>;
  start?: boolean; // New prop to control start
}

const Typewriter: React.FC<TypewriterProps> = ({ content, speed = 10, onComplete, containerRef, start = true }) => {
  const [displayedContent, setDisplayedContent] = useState('');
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    // Reset state when content prop changes or start is toggled off
    if (!start) {
        setDisplayedContent('');
        if (timeoutRef.current) clearTimeout(timeoutRef.current);
        return;
    }

    setDisplayedContent('');
    let currentIndex = 0;

    const type = () => {
      // Re-check current index against content length inside the recursive call context
      if (currentIndex < content.length) {
        let char = content[currentIndex];
        let nextIndex = currentIndex + 1;
        let delay = speed;

        // Handle HTML tags: skip typing animation for tags, render them instantly
        if (char === '<') {
          const closingTagIndex = content.indexOf('>', currentIndex);
          if (closingTagIndex !== -1) {
            nextIndex = closingTagIndex + 1;
            delay = 0; // Instant
          }
        }

        setDisplayedContent(content.substring(0, nextIndex));
        currentIndex = nextIndex;
        
        // Auto-scroll logic if container ref is provided
        if (containerRef && containerRef.current) {
          containerRef.current.scrollTop = containerRef.current.scrollHeight;
        }

        timeoutRef.current = setTimeout(type, delay);
      } else {
        if (onComplete) onComplete();
      }
    };

    // Initial delay or immediate start
    timeoutRef.current = setTimeout(type, 0);

    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, [content, speed, onComplete, containerRef, start]); // Re-run effect when content or start changes

  return (
    <div dangerouslySetInnerHTML={{ __html: displayedContent }} />
  );
};

export default Typewriter;
