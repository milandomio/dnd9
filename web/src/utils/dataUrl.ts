export function dataUrl(version: string, path: string) {
  if (!version) return path;
  const short = Number(version).toString(36);
  return path.replace('/data/json', `/data/${short}/json`);
}
