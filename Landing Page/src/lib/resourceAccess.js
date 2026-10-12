import { localStore } from './storage.js';
import { parseLoomId } from './video.js';

// Permisos de recursos.
//
// Un recurso (o una clase entera) con access:'team' NO trae su url ni su
// video en los datos públicos: solo los entrega el servidor
// (netlify/functions/recurso.js) cuando el equipo validó a la persona y le
// pasó un código. Acá vive la máquina de estados
//
//     locked → unlock_requested → unlocked
//
// y la abstracción `canAccessResource(userId, resourceId)`. Hoy el "usuario"
// es el navegador (proveedor local); cuando haya login se reemplaza el
// proveedor por uno que consulte la API y el resto de la app no cambia.

const STATUSES = ['locked', 'unlock_requested', 'unlocked'];

// La url de un recurso desbloqueado termina en un href: solo se acepta https.
function isSafeUrl(url) {
  try {
    return new URL(url).protocol === 'https:';
  } catch {
    return false;
  }
}

export function resourceStatus(resource, record) {
  if (resource.access !== 'team') return 'unlocked';
  if (!record || !STATUSES.includes(record.status)) return 'locked';
  if (record.status === 'unlocked' && !isSafeUrl(record.url)) return 'locked';
  return record.status;
}

export function nextAccessRecord(record, event) {
  if (event.type === 'grant') {
    return event.video
      ? { status: 'unlocked', url: event.url, video: event.video }
      : { status: 'unlocked', url: event.url };
  }
  if (event.type === 'request' && record?.status !== 'unlocked') return { status: 'unlock_requested' };
  return record;
}

const KEY = 'gustavo_crt_access_v1';
export const LOCAL_USER = 'local';

export function createLocalProvider(store = localStore) {
  return {
    async getRecord(_userId, resourceId) {
      return (store.read(KEY, {}) || {})[resourceId];
    },
    async setRecord(_userId, resourceId, record) {
      store.write(KEY, { ...(store.read(KEY, {}) || {}), [resourceId]: record });
    },
  };
}

export const accessProvider = createLocalProvider();

export async function canAccessResource(userId, resourceId, { provider = accessProvider } = {}) {
  const record = await provider.getRecord(userId, resourceId);
  return record?.status === 'unlocked' && isSafeUrl(record.url);
}

// Canjea el código que el equipo le pasó a la persona por la url del recurso.
export async function redeemUnlockCode(resourceId, code, { endpoint, fetchImpl = fetch }) {
  if (!endpoint) return { ok: false, reason: 'not_configured' };
  const cleanCode = String(code || '').trim();
  if (!cleanCode) return { ok: false, reason: 'invalid_code' };
  try {
    const response = await fetchImpl(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resourceId, code: cleanCode }),
    });
    if (!response.ok && response.status !== 403) return { ok: false, reason: 'unavailable' };
    const data = response.ok ? await response.json() : null;
    if (!isSafeUrl(data?.url)) return { ok: false, reason: 'invalid_code' };
    // El video llega como enlace de Loom o id de YouTube: cualquier otra cosa se descarta.
    return typeof data.video === 'string' && (parseLoomId(data.video) || /^[\w-]{11}$/.test(data.video))
      ? { ok: true, url: data.url, video: data.video }
      : { ok: true, url: data.url };
  } catch {
    return { ok: false, reason: 'network' };
  }
}
