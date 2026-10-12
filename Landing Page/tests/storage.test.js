import { describe, it, expect } from 'vitest';
import { createStore } from '../src/lib/storage.js';

function fakeStorage() {
  const data = new Map();
  return {
    getItem: (k) => (data.has(k) ? data.get(k) : null),
    setItem: (k, v) => data.set(k, String(v)),
  };
}

describe('createStore', () => {
  it('guarda y lee JSON', () => {
    const store = createStore(fakeStorage());
    store.write('k', { a: 1 });
    expect(store.read('k', null)).toEqual({ a: 1 });
  });

  it('devuelve el valor por defecto si la clave no existe', () => {
    expect(createStore(fakeStorage()).read('nada', { vacio: true })).toEqual({ vacio: true });
  });

  it('devuelve el valor por defecto si lo guardado no es JSON válido', () => {
    const storage = fakeStorage();
    storage.setItem('k', '{roto');
    expect(createStore(storage).read('k', 7)).toBe(7);
  });

  it('no revienta si el almacenamiento está bloqueado', () => {
    const blocked = {
      getItem: () => { throw new Error('SecurityError'); },
      setItem: () => { throw new Error('QuotaExceeded'); },
    };
    const store = createStore(blocked);
    expect(store.read('k', 'def')).toBe('def');
    expect(store.write('k', 1)).toBe(false);
  });

  it('funciona sin almacenamiento disponible', () => {
    const store = createStore(undefined);
    expect(store.write('k', 1)).toBe(false);
    expect(store.read('k', 2)).toBe(2);
  });
});
