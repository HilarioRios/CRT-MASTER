import { useEffect, useState } from 'react';

// Router mínimo por pathname (sin dependencia): la web original ya resolvía
// sus rutas así. Soporta segmentos dinámicos tipo "/school/:course".

const clean = (pathname) => pathname.replace(/\/+$/, '') || '/';

function decode(segment) {
  try {
    return decodeURIComponent(segment);
  } catch {
    return segment;
  }
}

export function matchRoute(pathname, routes) {
  const parts = clean(pathname).split('/');
  for (const route of routes) {
    const pattern = clean(route.path).split('/');
    if (pattern.length !== parts.length) continue;
    const params = {};
    const ok = pattern.every((piece, i) => {
      if (piece.startsWith(':')) {
        params[piece.slice(1)] = decode(parts[i]);
        return true;
      }
      return piece === parts[i];
    });
    if (ok) return { name: route.name, params };
  }
  return null;
}

const NAV_EVENT = 'app:navigate';

export function navigate(to, { replace = false, scroll = true } = {}) {
  window.history[replace ? 'replaceState' : 'pushState']({}, '', to);
  window.dispatchEvent(new Event(NAV_EVENT));
  if (scroll) window.scrollTo(0, 0);
}

// Devuelve el pathname y vuelve a renderizar también cuando solo cambia el
// query (?m=...), que algunas páginas leen.
const currentUrl = () => window.location.pathname + window.location.search;

export function usePathname() {
  const [url, setUrl] = useState(currentUrl);
  useEffect(() => {
    const sync = () => setUrl(currentUrl());
    window.addEventListener('popstate', sync);
    window.addEventListener(NAV_EVENT, sync);
    return () => {
      window.removeEventListener('popstate', sync);
      window.removeEventListener(NAV_EVENT, sync);
    };
  }, []);
  return url.split('?')[0];
}
