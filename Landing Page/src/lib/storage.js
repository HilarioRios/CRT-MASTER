// localStorage puede faltar o lanzar (modo incógnito, navegador embebido de
// Instagram/WhatsApp con el almacenamiento bloqueado). Nada de eso debe
// romper la página: se sigue usando, solo que sin memoria entre recargas.

export function createStore(storage) {
  return {
    read(key, fallback) {
      try {
        const raw = storage.getItem(key);
        return raw === null || raw === undefined ? fallback : JSON.parse(raw);
      } catch {
        return fallback;
      }
    },
    write(key, value) {
      try {
        storage.setItem(key, JSON.stringify(value));
        return true;
      } catch {
        return false;
      }
    },
  };
}

function browserStorage() {
  try {
    return window.localStorage;
  } catch {
    return undefined;
  }
}

export const localStore = createStore(typeof window === 'undefined' ? undefined : browserStorage());
