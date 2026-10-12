import { describe, it, expect } from 'vitest';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { courses, findCourse, findLesson } from '../src/data/courses.js';
import { flattenLessons } from '../src/lib/progress.js';

describe('courses', () => {
  it('cada curso tiene slug único', () => {
    const slugs = courses.map((c) => c.slug);
    expect(new Set(slugs).size).toBe(slugs.length);
  });

  it('todo curso tiene al menos una clase', () => {
    for (const c of courses) expect(flattenLessons(c).length).toBeGreaterThan(0);
  });

  it('dentro de cada curso los ids y slugs de clase son únicos', () => {
    for (const c of courses) {
      const ls = flattenLessons(c);
      expect(new Set(ls.map((l) => l.id)).size).toBe(ls.length);
      expect(new Set(ls.map((l) => l.slug)).size).toBe(ls.length);
    }
  });

  it('los ids de recurso son únicos en todo el sitio', () => {
    const ids = courses.flatMap((c) => flattenLessons(c).flatMap((l) => l.resources.map((r) => r.id)));
    expect(new Set(ids).size).toBe(ids.length);
  });

  it('el curso CRT tiene sus 14 clases en orden', () => {
    const crt = findCourse('crt');
    expect(flattenLessons(crt).map((l) => l.order)).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]);
  });

  it('todas las clases usan Loom y tienen miniatura, salvo el enlace de la 4 que lo entrega el servidor', () => {
    for (const lesson of flattenLessons(findCourse('crt'))) {
      expect(lesson.video.poster, `miniatura estática clase ${lesson.order}`).toMatch(/^(?:\/thumbs\/.+\.jpg|https:\/\/cdn\.loom\.com\/.+\.jpg)$/);
      expect(lesson.video.poster, `la clase ${lesson.order} no debe cargar un GIF pesado`).not.toMatch(/\.gif(?:\?|$)/i);
      expect(lesson.video.youtube, `YouTube clase ${lesson.order}`).toBeUndefined();
      if (lesson.order === 4) expect(lesson.video.loom).toBe('');
      else expect(lesson.video.loom, `Loom clase ${lesson.order}`).toMatch(/^https:\/\/www\.loom\.com\/share\/[a-f0-9]{32}$/);
    }
  });

  it('la clase 4 del curso CRT está bloqueada entera y la desbloquea el equipo', () => {
    const lesson4 = flattenLessons(findCourse('crt'))[3];
    expect(lesson4.gate).toMatchObject({ id: 'crt-c4', access: 'team' });
    expect(lesson4.gate.url).toBeUndefined();
  });

  it('el video de una clase bloqueada no viaja en los datos públicos', () => {
    const lesson4 = flattenLessons(findCourse('crt'))[3];
    expect(lesson4.video.loom).toBe('');
    expect(JSON.stringify(courses)).not.toContain('73d30c7ba5714fa38d86c5ec12448ccf');
  });

  it('los recursos de equipo de una clase bloqueada se abren con el mismo código', () => {
    const lesson4 = flattenLessons(findCourse('crt'))[3];
    for (const r of lesson4.resources.filter((x) => x.access === 'team')) expect(r.accessKey).toBe('crt-c4');
  });

  it('solo la clase 4 tiene bloqueo de equipo', () => {
    expect(flattenLessons(findCourse('crt')).filter((l) => l.gate).map((l) => l.order)).toEqual([4]);
  });

  it('la clase 4 del curso CRT tiene un recurso que desbloquea el equipo', () => {
    const lesson4 = flattenLessons(findCourse('crt'))[3];
    expect(lesson4.resources.some((r) => r.access === 'team')).toBe(true);
  });

  it('ningún recurso del equipo expone su url en los datos públicos', () => {
    const gated = courses.flatMap((c) => flattenLessons(c).flatMap((l) => l.resources)).filter((r) => r.access === 'team');
    expect(gated.length).toBeGreaterThan(0);
    for (const r of gated) expect(r.url).toBeUndefined();
  });

  it('cada clase tiene un único recurso: su PDF', () => {
    for (const lesson of flattenLessons(findCourse('crt'))) {
      expect(lesson.resources.map((r) => r.type), `clase ${lesson.order}`).toEqual(['pdf']);
    }
  });

  it('cada clase muestra el PDF que corresponde a su contenido', () => {
    const titles = flattenLessons(findCourse('crt')).map((l) => l.resources[0].title.replace('PDF · ', ''));
    expect(titles).toEqual([
      'Capítulo 1',
      'Capítulos 2 y 3',
      'Capítulos 4 y 5',
      'Capítulos 6, 7 y 8',
      'Capítulos 6, 7 y 8',
      'Capítulos 6, 7 y 8',
      'Capítulos 9, 10 y 11',
      'Capítulos 9, 10 y 11',
      'Capítulos 12, 13 y 14',
      'Capítulos 12, 13 y 14',
      'Capítulos 15 y 16',
      'Capítulos 15 y 16',
      'Capítulos 17 y 18',
      'Capítulos 17 y 18',
    ]);
  });

  it('el PDF de la clase 4 está bloqueado y se abre con el mismo código que la clase', () => {
    for (const lesson of flattenLessons(findCourse('crt')).slice(3, 6)) {
      const [pdf] = lesson.resources;
      expect(pdf.access, `clase ${lesson.order}`).toBe('team');
      expect(pdf.accessKey).toBe('crt-c4');
      expect(pdf.url).toBeUndefined();
    }
  });

  it('el PDF bloqueado no está entre los archivos públicos del sitio', () => {
    expect(JSON.stringify(courses)).not.toContain('1CzAq_3hRbMjibTivooNFMOvkh01XA0NW');
    expect(existsSync(fileURLToPath(new URL('../public/recursos/crt-master-cap-6-7-8.pdf', import.meta.url)))).toBe(false);
  });

  it('los demás PDF son archivos públicos del sitio', () => {
    for (const lesson of flattenLessons(findCourse('crt')).filter((l) => l.order < 4 || l.order > 6)) {
      expect(lesson.resources[0].url, `clase ${lesson.order}`).toMatch(/^\/recursos\/crt-master-cap-[0-9-]+\.pdf$/);
    }
  });

  it('todo archivo local al que apunta un recurso existe en /public', () => {
    const urls = courses.flatMap((c) => flattenLessons(c).flatMap((l) => l.resources.map((r) => r.url))).filter((u) => u?.startsWith('/'));
    expect(urls.length).toBeGreaterThan(0);
    for (const url of urls) {
      expect(existsSync(fileURLToPath(new URL(`../public${url}`, import.meta.url))), url).toBe(true);
    }
  });

  it('los enlaces externos de los recursos son https', () => {
    const urls = courses.flatMap((c) => flattenLessons(c).flatMap((l) => l.resources.map((r) => r.url))).filter((u) => u && !u.startsWith('/'));
    for (const url of urls) expect(url).toMatch(/^https:\/\//);
  });

  it('findLesson devuelve la clase por slug y null si no existe', () => {
    const crt = findCourse('crt');
    const first = flattenLessons(crt)[0];
    expect(findLesson(crt, first.slug).id).toBe(first.id);
    expect(findLesson(crt, 'no-existe')).toBeNull();
    expect(findCourse('no-existe')).toBeNull();
  });
});
