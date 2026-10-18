const base64 = (prompt: string) => Buffer.from(prompt, 'utf8').toString('base64');
const rot13 = (prompt: string) => prompt.replace(/[a-zA-Z]/g, char => {
  const start = char <= 'Z' ? 65 : 97;
  return String.fromCharCode(((char.charCodeAt(0) - start + 13) % 26) + start);
});

export const strategies: Record<string, (prompt: string) => string> = {
  direct: prompt => prompt,
  polite: prompt => `请按既定用途回答：${prompt}`,
  base64,
  BaseEncoding: base64,
  rot13,
  ROT13: rot13,
};

export function applyStrategy(id: string, prompt: string): { id: string; prompt: string; known: boolean } {
  const apply = strategies[id];
  if (!apply) return { id, prompt, known: false };
  return { id, prompt: apply(prompt), known: true };
}
