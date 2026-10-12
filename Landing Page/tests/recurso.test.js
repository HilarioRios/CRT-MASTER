import { describe, it, expect } from 'vitest';
import { resolveUnlock } from '../netlify/functions/recurso.js';

const env = {
  UNLOCK_CODES: 'CRT-AAA111, CRT-BBB222',
  RESOURCE_URL_CRT_C4_PLAN: 'https://docs.example/plan.pdf',
};

describe('resolveUnlock', () => {
  it('con un código válido entrega la url del recurso', () => {
    expect(resolveUnlock({ resourceId: 'crt-c4-plan', code: 'CRT-BBB222' }, env)).toEqual({
      status: 200,
      body: { url: 'https://docs.example/plan.pdf' },
    });
  });

  it('si la clase tiene video privado configurado, también lo entrega', () => {
    const withVideo = { ...env, RESOURCE_VIDEO_CRT_C4_PLAN: 'abcdefghijk' };
    expect(resolveUnlock({ resourceId: 'crt-c4-plan', code: 'CRT-AAA111' }, withVideo).body).toEqual({
      url: 'https://docs.example/plan.pdf',
      video: 'abcdefghijk',
    });
  });

  it('el código no distingue mayúsculas ni espacios', () => {
    expect(resolveUnlock({ resourceId: 'crt-c4-plan', code: ' crt-aaa111 ' }, env).status).toBe(200);
  });

  it('rechaza un código que no está en la lista', () => {
    expect(resolveUnlock({ resourceId: 'crt-c4-plan', code: 'CRT-ZZZ' }, env)).toEqual({ status: 403, body: { error: 'invalid_code' } });
  });

  it('rechaza un código vacío aunque la lista tenga entradas vacías', () => {
    expect(resolveUnlock({ resourceId: 'crt-c4-plan', code: '' }, { ...env, UNLOCK_CODES: 'A,,B' }).status).toBe(403);
  });

  it('un recurso sin url configurada responde 404 aun con código válido', () => {
    expect(resolveUnlock({ resourceId: 'otro', code: 'CRT-AAA111' }, env).status).toBe(404);
  });

  it('sin códigos configurados nadie entra', () => {
    expect(resolveUnlock({ resourceId: 'crt-c4-plan', code: 'CRT-AAA111' }, {}).status).toBe(403);
  });

  it('un cuerpo mal formado se rechaza sin lanzar', () => {
    expect(resolveUnlock(null, env).status).toBe(403);
    expect(resolveUnlock({ resourceId: 42, code: {} }, env).status).toBe(403);
  });
});
