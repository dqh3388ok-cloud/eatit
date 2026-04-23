/**
 * Mask an API key for display.
 *
 *   sk-proj-abcdef1234567890    -> sk-proj-ab•••••••7890
 *   short                       -> •••••
 */
export function maskApiKey(key: string): string {
  if (!key) return "";
  const trimmed = key.trim();
  if (trimmed.length <= 8) return "•".repeat(trimmed.length);

  const head = trimmed.slice(0, Math.min(8, trimmed.length - 4));
  const tail = trimmed.slice(-4);
  return `${head}${"•".repeat(7)}${tail}`;
}
