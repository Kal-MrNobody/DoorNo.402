const PATTERNS: RegExp[] = [
  /\$\s*([\d,]+\.?\d*)/,
  /([\d,]+\.?\d*)\s*(?:USD|USDC|dollars?)/i,
];

export function extractPrice(description: string): number | null {
  for (const p of PATTERNS) {
    const m = description.match(p);
    if (m) return parseFloat(m[1].replace(/,/g, ""));
  }
  return null;
}
