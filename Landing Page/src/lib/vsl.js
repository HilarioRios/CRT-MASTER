import { localStore } from './storage.js';

// Estado de la VSL: si la persona ya terminó el video, la sección de agenda
// queda abierta aunque recargue. Va atado a la versión del video: si se
// cambia la VSL (config/brand.js → vsl.version), hay que verla de nuevo.

const KEY = 'gustavo_crt_vsl_v1';

export function isVslUnlocked(record, version) {
  return Boolean(record && record.completed === true && record.version === version);
}

export function readVslUnlocked(version, store = localStore) {
  return isVslUnlocked(store.read(KEY, null), version);
}

export function saveVslCompleted(version, store = localStore) {
  return store.write(KEY, { completed: true, version, at: Date.now() });
}
