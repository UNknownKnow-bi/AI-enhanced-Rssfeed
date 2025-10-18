import DOMPurify from 'dompurify';

/**
 * Sanitize HTML content from RSS feeds to prevent XSS attacks
 * and ensure safe rendering in the browser
 */
export function sanitizeHTMLContent(html: string): string {
  if (!html) return '';

  // Configure DOMPurify with strict security settings
  const config: any = {
    // Allow only safe HTML tags for article content
    ALLOWED_TAGS: [
      'p', 'br', 'span', 'div',
      'a', 'strong', 'b', 'em', 'i', 'u', 's', 'mark',
      'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
      'ul', 'ol', 'li',
      'blockquote', 'q', 'cite',
      'code', 'pre',
      'img',
      'table', 'thead', 'tbody', 'tr', 'th', 'td',
      'hr',
      'sup', 'sub',
      'abbr', 'time',
      'figure', 'figcaption',
    ],

    // Allow only safe attributes
    ALLOWED_ATTR: [
      'href', 'src', 'alt', 'title',
      'class', 'id',
      'width', 'height',
      'target', 'rel',
      'datetime',
      'cite',
    ],

    // Only allow http/https protocols (block javascript:, data:, etc.)
    ALLOWED_URI_REGEXP: /^(?:(?:(?:f|ht)tps?):)\/\//i,

    // Add target="_blank" and rel="noopener noreferrer" to all links
    ADD_ATTR: ['target', 'rel'],

    // Remove all data attributes
    FORBID_ATTR: [
      'onclick', 'onload', 'onerror', 'onmouseover',
      'style', // Remove inline styles for consistency
    ],

    // Forbid dangerous tags
    FORBID_TAGS: [
      'script', 'iframe', 'embed', 'object',
      'form', 'input', 'button', 'textarea',
      'link', 'style',
      'video', 'audio', 'source',
      'svg', 'math',
    ],

    // Keep safe HTML
    KEEP_CONTENT: true,
    RETURN_DOM: false,
    RETURN_DOM_FRAGMENT: false,
    RETURN_DOM_IMPORT: false,
  };

  // Sanitize the HTML - explicitly cast to string
  let sanitized = String(DOMPurify.sanitize(html, config));

  // Post-processing: ensure all external links have security attributes
  sanitized = sanitized.replace(
    /<a\s+([^>]*href=["'][^"']*["'][^>]*)>/gi,
    (_match: string, attrs: string) => {
      // Add target and rel if not present
      let newAttrs = attrs;
      if (!newAttrs.includes('target=')) {
        newAttrs += ' target="_blank"';
      }
      if (!newAttrs.includes('rel=')) {
        newAttrs += ' rel="noopener noreferrer"';
      }
      return `<a ${newAttrs}>`;
    }
  );

  // Post-processing: add loading="lazy" to images
  sanitized = sanitized.replace(
    /<img\s+([^>]*)>/gi,
    (_match: string, attrs: string) => {
      let newAttrs = attrs;
      if (!newAttrs.includes('loading=')) {
        newAttrs += ' loading="lazy"';
      }
      // Add error handling class for broken images
      if (!newAttrs.includes('class=')) {
        newAttrs += ' class="article-image"';
      }
      return `<img ${newAttrs}>`;
    }
  );

  return sanitized;
}

/**
 * Strip all HTML tags and return plain text
 * Useful for generating summaries or previews
 */
export function stripHTMLTags(html: string): string {
  if (!html) return '';

  // First sanitize to remove dangerous content
  const sanitized = String(DOMPurify.sanitize(html, {
    ALLOWED_TAGS: [],
    KEEP_CONTENT: true,
  }));

  // Clean up excessive whitespace
  return sanitized
    .replace(/\s+/g, ' ')
    .replace(/\n+/g, '\n')
    .trim();
}

/**
 * Truncate content to a maximum length while preserving word boundaries
 */
export function truncateContent(content: string, maxLength: number = 5000): string {
  if (!content || content.length <= maxLength) return content;

  // Try to truncate at a closing tag to maintain HTML validity
  const truncated = content.substring(0, maxLength);
  const lastClosingTag = truncated.lastIndexOf('</');

  if (lastClosingTag > maxLength * 0.8) {
    // If we found a closing tag in the last 20% of content, cut there
    return truncated.substring(0, lastClosingTag + truncated.substring(lastClosingTag).indexOf('>') + 1);
  }

  // Otherwise just truncate and add ellipsis
  return truncated + '...';
}
