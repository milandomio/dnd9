export function dataUrl(version: string, path: string) {
  if (!version) throw new Error('Data version is not ready');
  const cacheVersion = /^v[0-9a-f]{24}$/.test(version)
    ? `r-${version}`
    : version === 'dev'
      ? version
      : Number(version).toString(36);
  if (!path.startsWith('/data/')) return path;
  return path.replace(/^\/data\//, `/data/${cacheVersion}/`);
}
