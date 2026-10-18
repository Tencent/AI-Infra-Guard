function ipv4(value: string): boolean {
  const parts = value.split('.');
  return parts.length === 4 && parts.every(part => /^\d{1,3}$/.test(part) && Number(part) <= 255);
}

function ipv6(value: string): boolean {
  const host = value.replace(/^\[|\]$/g, '');
  if (!host.includes(':') || !/^[0-9a-f:]+$/i.test(host) || (host.match(/::/g) || []).length > 1) return false;
  const groups = host.split('::').flatMap(part => (part ? part.split(':') : []));
  if (!groups.every(group => /^[0-9a-f]{1,4}$/i.test(group))) return false;
  return host.includes('::') ? groups.length < 8 : groups.length === 8;
}

function domain(value: string): boolean {
  if (value.toLowerCase() === 'localhost') return true;
  if (value.length > 253) return false;
  const labels = value.split('.');
  const tld = labels[labels.length - 1] || '';
  if (labels.length < 2 || !/^[a-z]{2,}$/i.test(tld)) return false;
  return labels.every(label => /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/i.test(label));
}

function host(value: string): boolean {
  return ipv4(value) || ipv6(value) || domain(value);
}

export function isScanTarget(value: string): boolean {
  const target = value.trim();
  if (!target || /\s/.test(target)) return false;
  if (target.includes('://')) {
    try {
      const url = new URL(target);
      return (url.protocol === 'http:' || url.protocol === 'https:') && host(url.hostname);
    } catch {
      return false;
    }
  }
  const slash = target.lastIndexOf('/');
  if (slash > 0) {
    const prefix = Number(target.slice(slash + 1));
    const address = target.slice(0, slash);
    if (!Number.isInteger(prefix)) return false;
    if (ipv4(address)) return prefix >= 0 && prefix <= 32;
    if (ipv6(address)) return prefix >= 0 && prefix <= 128;
    return false;
  }
  return host(target);
}
