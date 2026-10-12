import { describe, it, expect } from 'vitest';
import {
  emptyProgress,
  flattenLessons,
  markCompleted,
  setLessonPercent,
  lessonState,
  coursePercent,
  nextLesson,
  adjacentLessons,
} from '../src/lib/progress.js';

const course = (unlockMode = 'sequential') => ({
  id: 'c',
  unlockMode,
  modules: [
    { id: 'm1', lessons: [{ id: 'a' }, { id: 'b' }] },
    { id: 'm2', lessons: [{ id: 'c' }, { id: 'd' }] },
  ],
});

describe('flattenLessons', () => {
  it('devuelve las clases de todos los módulos en orden', () => {
    expect(flattenLessons(course()).map((l) => l.id)).toEqual(['a', 'b', 'c', 'd']);
  });
});

describe('lessonState', () => {
  it('en modo secuencial solo la primera clase arranca disponible', () => {
    const p = emptyProgress();
    expect(lessonState(course(), p, 'a')).toBe('available');
    expect(lessonState(course(), p, 'b')).toBe('locked');
  });

  it('completar una clase desbloquea la siguiente, también entre módulos', () => {
    const p = markCompleted(markCompleted(emptyProgress(), 'a'), 'b');
    expect(lessonState(course(), p, 'b')).toBe('completed');
    expect(lessonState(course(), p, 'c')).toBe('available');
    expect(lessonState(course(), p, 'd')).toBe('locked');
  });

  it('en modo abierto ninguna clase está bloqueada', () => {
    expect(lessonState(course('open'), emptyProgress(), 'd')).toBe('available');
  });

  it('una clase marcada como locked en los datos queda bloqueada aunque el curso sea abierto', () => {
    const c = course('open');
    c.modules[1].lessons[1].locked = true;
    expect(lessonState(c, emptyProgress(), 'd')).toBe('locked');
  });
});

describe('markCompleted', () => {
  it('no muta el progreso recibido', () => {
    const p = emptyProgress();
    markCompleted(p, 'a');
    expect(p).toEqual(emptyProgress());
  });
});

describe('setLessonPercent', () => {
  it('guarda el porcentaje visto y nunca lo baja', () => {
    let p = setLessonPercent(emptyProgress(), 'a', 60);
    p = setLessonPercent(p, 'a', 20);
    expect(p.lessons.a.percent).toBe(60);
  });

  it('acota el valor entre 0 y 100', () => {
    expect(setLessonPercent(emptyProgress(), 'a', 140).lessons.a.percent).toBe(100);
    expect(setLessonPercent(emptyProgress(), 'a', -5).lessons.a.percent).toBe(0);
  });

  it('ver el 100% no marca la clase como completada por sí solo', () => {
    const p = setLessonPercent(emptyProgress(), 'a', 100);
    expect(lessonState(course(), p, 'a')).toBe('available');
  });
});

describe('coursePercent', () => {
  it('es el porcentaje de clases completadas, redondeado', () => {
    expect(coursePercent(course(), emptyProgress())).toBe(0);
    expect(coursePercent(course(), markCompleted(emptyProgress(), 'a'))).toBe(25);
  });

  it('ignora ids completados que ya no existen en el curso', () => {
    expect(coursePercent(course(), markCompleted(emptyProgress(), 'vieja'))).toBe(0);
  });

  it('un curso sin clases da 0 y no NaN', () => {
    expect(coursePercent({ modules: [] }, emptyProgress())).toBe(0);
  });
});

describe('nextLesson', () => {
  it('es la primera clase sin completar', () => {
    expect(nextLesson(course(), markCompleted(emptyProgress(), 'a')).id).toBe('b');
  });

  it('es null cuando el curso está completo', () => {
    const p = ['a', 'b', 'c', 'd'].reduce(markCompleted, emptyProgress());
    expect(nextLesson(course(), p)).toBeNull();
  });
});

describe('adjacentLessons', () => {
  it('devuelve la anterior y la siguiente cruzando módulos', () => {
    const { prev, next } = adjacentLessons(course(), 'c');
    expect(prev.id).toBe('b');
    expect(next.id).toBe('d');
  });

  it('en los extremos devuelve null', () => {
    expect(adjacentLessons(course(), 'a').prev).toBeNull();
    expect(adjacentLessons(course(), 'd').next).toBeNull();
  });
});
