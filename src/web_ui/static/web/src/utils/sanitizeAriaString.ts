/**
 * Sanitizes a string for safe use in ARIA attributes.
 * Removes or escapes characters that could be used for injection.
 * Only allows alphanumeric, space, dash, underscore, and period.
 */
export function sanitizeAriaString(value: string | undefined): string | undefined {
  if (typeof value !== "string") return undefined;
  return value.replace(/[^a-zA-Z0-9 _.\-]/g, "");
}