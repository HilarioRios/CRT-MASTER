import { describe, it, expect } from 'vitest';
import {
  resourceStatus,
  nextAccessRecord,
  canAccessResource,
  redeemUnlockCode,
  createLocalProvider,
} from '../src/lib/resourceAccess.js';

const open = { id: 'pdf-1', access: 'public', url: '/docs/a.pdf' };
const gated = { id: 'crt-checklist', access: 'team' };

describe('resourceStatus', () => {
  it('un recurso público está disponible sin registro', () => {
    expect(resourceStatus(open, undefined)).toBe('unlocked');
  });

  it('un recurso del equipo arranca bloqueado', () => {
    expect(resourceStatus(gated, undefined)).toBe('locked');
  });

  it('refleja el estado guardado', () => {
    expect(resourceStatus(gated, { status: 'unlock_requested' })).toBe('unlock_requested');
    expect(resourceStatus(gated, { status: 'unlocked', url: 'https://x' })).toBe('unlocked');
  });

  it('un estado guardado desconocido se trata como bloqueado', () => {
    expect(resourceStatus(gated, { status: 'hackeado' })).toBe('locked');
  });

  it('un "unlocked" guardado sin url no cuenta como desbloqueado', () => {
    expect(resourceStatus(gated, { status: 'unlocked' })).toBe('locked');
  });

  it('un "unlocked" guardado con una url que no es https no cuenta como desbloqueado', () => {
    expect(resourceStatus(gated, { status: 'unlocked', url: 'javascript:alert(1)' })).toBe('locked');
    expect(resourceStatus(gated, { status: 'unlocked', url: 'no es una url' })).toBe('locked');
  });
});

describe('nextAccessRecord', () => {
  it('pedir el desbloqueo pasa de locked a unlock_requested', () => {
    expect(nextAccessRecord(undefined, { type: 'request' }).status).toBe('unlock_requested');
  });

  it('otorgar el acceso guarda la url y pasa a unlocked', () => {
    expect(nextAccessRecord({ status: 'unlock_requested' }, { type: 'grant', url: 'https://x' })).toEqual({
      status: 'unlocked',
      url: 'https://x',
    });
  });

  it('otorgar el acceso a una clase guarda también su video', () => {
    expect(nextAccessRecord(undefined, { type: 'grant', url: 'https://x', video: 'abcdefghijk' })).toEqual({
      status: 'unlocked',
      url: 'https://x',
      video: 'abcdefghijk',
    });
  });

  it('volver a pedir no degrada un recurso ya desbloqueado', () => {
    const rec = { status: 'unlocked', url: 'https://x' };
    expect(nextAccessRecord(rec, { type: 'request' })).toEqual(rec);
  });
});

describe('createLocalProvider', () => {
  it('no revienta si lo guardado no es un objeto', async () => {
    const provider = createLocalProvider({ read: () => null, write: () => true });
    expect(await provider.getRecord('u', 'r')).toBeUndefined();
  });
});

describe('canAccessResource', () => {
  it('consulta al proveedor por usuario y recurso', async () => {
    const provider = { getRecord: async (userId, id) => (userId === 'u1' && id === 'r' ? { status: 'unlocked', url: 'https://x' } : undefined) };
    expect(await canAccessResource('u1', 'r', { provider })).toBe(true);
    expect(await canAccessResource('u2', 'r', { provider })).toBe(false);
  });
});

describe('redeemUnlockCode', () => {
  const ok = async () => ({ ok: true, json: async () => ({ url: 'https://docs/x.pdf' }) });

  it('sin endpoint configurado avisa que el desbloqueo no está conectado', async () => {
    expect(await redeemUnlockCode('r', 'ABC', { endpoint: '', fetchImpl: ok })).toEqual({ ok: false, reason: 'not_configured' });
  });

  it('con código válido devuelve la url que entrega el servidor', async () => {
    const calls = [];
    const fetchImpl = async (url, init) => { calls.push([url, JSON.parse(init.body)]); return ok(); };
    const res = await redeemUnlockCode('r', '  abc-123 ', { endpoint: '/api/recurso', fetchImpl });
    expect(res).toEqual({ ok: true, url: 'https://docs/x.pdf' });
    expect(calls[0]).toEqual(['/api/recurso', { resourceId: 'r', code: 'abc-123' }]);
  });

  it('devuelve el video de la clase cuando el servidor lo entrega', async () => {
    const fetchImpl = async () => ({ ok: true, json: async () => ({ url: 'https://docs/x.pdf', video: 'abcdefghijk' }) });
    expect(await redeemUnlockCode('r', 'abc', { endpoint: '/api/recurso', fetchImpl })).toEqual({ ok: true, url: 'https://docs/x.pdf', video: 'abcdefghijk' });
  });

  it('devuelve el video cuando el servidor entrega un enlace de Loom', async () => {
    const loom = 'https://www.loom.com/share/bcbeb3d2c19d41ae87ff4a045f18d429';
    const fetchImpl = async () => ({ ok: true, json: async () => ({ url: 'https://docs/x.pdf', video: loom }) });
    expect(await redeemUnlockCode('r', 'abc', { endpoint: '/api/recurso', fetchImpl })).toEqual({ ok: true, url: 'https://docs/x.pdf', video: loom });
  });

  it('descarta un enlace de video que no es de Loom', async () => {
    const fetchImpl = async () => ({ ok: true, json: async () => ({ url: 'https://docs/x.pdf', video: 'https://evil.example/share/bcbeb3d2c19d41ae87ff4a045f18d429' }) });
    expect(await redeemUnlockCode('r', 'abc', { endpoint: '/api/recurso', fetchImpl })).toEqual({ ok: true, url: 'https://docs/x.pdf' });
  });

  it('descarta un video que no es un id de YouTube ni un enlace de Loom', async () => {
    const fetchImpl = async () => ({ ok: true, json: async () => ({ url: 'https://docs/x.pdf', video: '"><script>' }) });
    expect(await redeemUnlockCode('r', 'abc', { endpoint: '/api/recurso', fetchImpl })).toEqual({ ok: true, url: 'https://docs/x.pdf' });
  });

  it('con código rechazado devuelve invalid_code', async () => {
    const fetchImpl = async () => ({ ok: false, status: 403, json: async () => ({}) });
    expect(await redeemUnlockCode('r', 'mal', { endpoint: '/api/recurso', fetchImpl })).toEqual({ ok: false, reason: 'invalid_code' });
  });

  it('si la red falla devuelve network y no lanza', async () => {
    const fetchImpl = async () => { throw new Error('offline'); };
    expect(await redeemUnlockCode('r', 'abc', { endpoint: '/api/recurso', fetchImpl })).toEqual({ ok: false, reason: 'network' });
  });

  it('una url que no es https en la respuesta no desbloquea', async () => {
    const fetchImpl = async () => ({ ok: true, json: async () => ({ url: 'javascript:alert(1)' }) });
    expect((await redeemUnlockCode('r', 'abc', { endpoint: '/api/recurso', fetchImpl })).ok).toBe(false);
  });

  it('si el servidor no tiene el recurso configurado no culpa al código', async () => {
    const fetchImpl = async () => ({ ok: false, status: 404, json: async () => ({}) });
    expect(await redeemUnlockCode('r', 'abc', { endpoint: '/api/recurso', fetchImpl })).toEqual({ ok: false, reason: 'unavailable' });
  });

  it('una respuesta ok sin url no desbloquea', async () => {
    const fetchImpl = async () => ({ ok: true, json: async () => ({}) });
    expect(await redeemUnlockCode('r', 'abc', { endpoint: '/api/recurso', fetchImpl })).toEqual({ ok: false, reason: 'invalid_code' });
  });

  it('un código vacío no llega al servidor', async () => {
    let called = false;
    const fetchImpl = async () => { called = true; return ok(); };
    expect((await redeemUnlockCode('r', '   ', { endpoint: '/api/recurso', fetchImpl })).reason).toBe('invalid_code');
    expect(called).toBe(false);
  });
});
