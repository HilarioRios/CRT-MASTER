import { useSyncExternalStore } from 'react';
import { localStore } from './storage.js';
import { emptyProgress } from './progress.js';

// Persistencia del progreso. Hoy: localStorage, por navegador. Para migrar a
// progreso por usuario alcanza con reemplazar `load` y `persist` por llamadas
// a la API: los componentes solo conocen useCourseProgress/updateCourseProgress.

const KEY = 'gustavo_crt_progress_v1';
const EMPTY = emptyProgress();

function load() {
  const saved = localStore.read(KEY, {});
  if (!saved || typeof saved !== 'object' || Array.isArray(saved)) return {};
  const valid = {};
  for (const [courseId, progress] of Object.entries(saved)) {
    if (progress && typeof progress.lessons === 'object' && progress.lessons !== null) {
      valid[courseId] = { lessons: progress.lessons, lastLessonId: progress.lastLessonId ?? null };
    }
  }
  return valid;
}

const persist = (all) => localStore.write(KEY, all);

let state = load();
const listeners = new Set();

const emit = () => listeners.forEach((listener) => listener());

const subscribe = (listener) => {
  listeners.add(listener);
  return () => listeners.delete(listener);
};

// Otra pestaña guardó progreso: se toma el suyo para no pisarlo después.
if (typeof window !== 'undefined') {
  window.addEventListener('storage', (event) => {
    if (event.key !== KEY) return;
    state = load();
    emit();
  });
}

export function updateCourseProgress(courseId, change) {
  const current = state[courseId] || EMPTY;
  const next = change(current);
  if (next === current) return;
  state = { ...state, [courseId]: next };
  persist(state);
  emit();
}

export function useAllProgress() {
  return useSyncExternalStore(subscribe, () => state);
}

export function useCourseProgress(courseId) {
  return useAllProgress()[courseId] || EMPTY;
}
