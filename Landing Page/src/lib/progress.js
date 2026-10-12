// Lógica pura del progreso de un curso. No sabe dónde se guarda: hoy lo
// persiste progressStore.js en localStorage; mañana puede ser una API por
// usuario sin tocar nada de acá.
//
// Forma del progreso de un curso:
//   { lessons: { [lessonId]: { completed: boolean, percent: number } }, lastLessonId }

export function emptyProgress() {
  return { lessons: {}, lastLessonId: null };
}

export function flattenLessons(course) {
  return (course.modules || []).flatMap((m) => m.lessons || []);
}

function patchLesson(progress, lessonId, patch) {
  const current = progress.lessons[lessonId] || { completed: false, percent: 0 };
  return {
    ...progress,
    lessons: { ...progress.lessons, [lessonId]: { ...current, ...patch } },
  };
}

export function markCompleted(progress, lessonId) {
  return patchLesson(progress, lessonId, { completed: true });
}

export function setLessonPercent(progress, lessonId, percent) {
  const bounded = Math.max(0, Math.min(100, Math.round(Number(percent) || 0)));
  const previous = progress.lessons[lessonId]?.percent || 0;
  return patchLesson(progress, lessonId, { percent: Math.max(previous, bounded) });
}

export function setLastLesson(progress, lessonId) {
  return progress.lastLessonId === lessonId ? progress : { ...progress, lastLessonId: lessonId };
}

const isCompleted = (progress, lessonId) => progress.lessons[lessonId]?.completed === true;

// 'completed' | 'available' | 'locked'
export function lessonState(course, progress, lessonId) {
  if (isCompleted(progress, lessonId)) return 'completed';
  const lessons = flattenLessons(course);
  const index = lessons.findIndex((l) => l.id === lessonId);
  if (index === -1 || lessons[index].locked) return 'locked';
  if (course.unlockMode !== 'sequential' || index === 0) return 'available';
  return isCompleted(progress, lessons[index - 1].id) ? 'available' : 'locked';
}

export function completedCount(course, progress) {
  return flattenLessons(course).filter((l) => isCompleted(progress, l.id)).length;
}

export function coursePercent(course, progress) {
  const total = flattenLessons(course).length;
  return total ? Math.round((completedCount(course, progress) / total) * 100) : 0;
}

export function nextLesson(course, progress) {
  return flattenLessons(course).find((l) => !isCompleted(progress, l.id)) || null;
}

export function adjacentLessons(course, lessonId) {
  const lessons = flattenLessons(course);
  const index = lessons.findIndex((l) => l.id === lessonId);
  return {
    prev: index > 0 ? lessons[index - 1] : null,
    next: index !== -1 && index < lessons.length - 1 ? lessons[index + 1] : null,
  };
}
