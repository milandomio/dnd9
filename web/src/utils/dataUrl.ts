declare const __DATA_VERSION__: string | undefined;

let _version = typeof __DATA_VERSION__ !== 'undefined' ? __DATA_VERSION__ : '';

export function setDataVersion(v: string) {
  if (v && (!_version || Number(v) > Number(_version))) {
    _version = v;
  }
}

export function getDataVersion(): string {
  return _version;
}

export function dataUrl(path: string): string {
  if (!_version) return path;
  // /data/json/foo → /data/<base36>/json/foo  (versioned for CDN cache busting)
  // /data/img/foo stays as-is (images rarely change)
  if (path.startsWith('/data/json/')) {
    const short = Number(_version).toString(36);
    return `/data/${short}${path.slice(5)}`;
  }
  return path;
}
