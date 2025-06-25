// src/utils/sanitize.ts
/**
 * Minimal HTML sanitizer for toast content.
 * Removes all tags except basic formatting, strips scripts/styles, and escapes dangerous chars.
 * For toasts, only allow plain text or very limited inline tags if needed.
 */
export function sanitize(input: string): string {
  // Remove script/style tags and their content
  let sanitized = input.replace(/<script[\s\S]*?>[\s\S]*?<\/script>/gi, '')
                       .replace(/<style[\s\S]*?>[\s\S]*?<\/style>/gi, '');
  // Remove all HTML tags
  sanitized = sanitized.replace(/<\/?[^>]+(>|$)/g, '');
  // Escape angle brackets
  sanitized = sanitized.replace(/</g, '<').replace(/>/g, '>');
  // Remove event handler attributes (not needed for plain text)
  return sanitized;
}