import { describe, it, expect } from 'vitest';
import { matchRoute } from '../src/lib/router.js';

const routes = [
  { name: 'landing', path: '/' },
  { name: 'school', path: '/school' },
  { name: 'course', path: '/school/:course' },
  { name: 'lesson', path: '/school/:course/:lesson' },
];

describe('matchRoute', () => {
  it('encuentra la ruta raíz', () => {
    expect(matchRoute('/', routes)).toEqual({ name: 'landing', params: {} });
  });

  it('extrae los parámetros de una ruta dinámica', () => {
    expect(matchRoute('/school/crt/modelo-de-entrada', routes)).toEqual({
      name: 'lesson',
      params: { course: 'crt', lesson: 'modelo-de-entrada' },
    });
  });

  it('ignora la barra final', () => {
    expect(matchRoute('/school/', routes)).toEqual({ name: 'school', params: {} });
  });

  it('decodifica los parámetros', () => {
    expect(matchRoute('/school/an%C3%A1lisis', routes).params.course).toBe('análisis');
  });

  it('devuelve null si ninguna ruta coincide', () => {
    expect(matchRoute('/no/existe/para/nada', routes)).toBeNull();
  });

  it('no revienta con un parámetro mal codificado', () => {
    expect(matchRoute('/school/%E0%A4%A', routes)).toEqual({
      name: 'course',
      params: { course: '%E0%A4%A' },
    });
  });
});
