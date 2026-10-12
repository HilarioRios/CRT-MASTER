import { completedCount, coursePercent, flattenLessons, lessonState } from '../lib/progress.js';
import { CheckIcon, LockIcon, PlayIcon } from './Icons.jsx';
import { CourseProgress } from './CourseProgress.jsx';
import { Link } from './Link.jsx';

function Marker({ state, current, order }) {
  if (state === 'completed') return <span className="item-marca hecha"><CheckIcon size={11} /></span>;
  if (state === 'locked') return <span className="item-marca cerrada"><LockIcon size={12} /></span>;
  if (current) return <span className="item-marca actual"><PlayIcon size={12} /></span>;
  return <span className="item-marca">{String(order).padStart(2, '0')}</span>;
}

const STATE_TEXT = { completed: 'Completada', locked: 'Bloqueada', available: 'Disponible' };

// El contenido del curso: qué clase estás viendo, cuáles terminaste, cuál
// sigue y cuáles están bloqueadas. Se usa en la clase y en la página del curso.
export function LessonSidebar({ course, progress, currentLessonId = null }) {
  const total = flattenLessons(course).length;
  const done = completedCount(course, progress);
  const showModules = course.modules.length > 1;

  return (
    <aside className="contenido" aria-label="Contenido del curso">
      <header className="contenido-head">
        <b>Contenido</b>
        <span>{done}/{total}</span>
      </header>
      <CourseProgress percent={coursePercent(course, progress)} />
      {course.modules.map((module) => (
        <section key={module.id}>
          {showModules && <p className="contenido-modulo">{module.title}</p>}
          <ol className="contenido-lista">
            {module.lessons.map((lesson) => {
              const state = lessonState(course, progress, lesson.id);
              const current = lesson.id === currentLessonId;
              const body = (
                <>
                  <Marker state={state} current={current} order={lesson.order} />
                  <span className="item-textos">
                    <span className="item-titulo">{lesson.title}</span>
                    <span className="item-meta">
                      {current ? 'Viendo ahora' : STATE_TEXT[state]}
                      {lesson.duration ? ` · ${lesson.duration}` : ''}
                    </span>
                  </span>
                </>
              );
              return (
                <li key={lesson.id}>
                  {state === 'locked' ? (
                    <span className="item cerrada" aria-disabled="true">{body}</span>
                  ) : (
                    <Link
                      className={`item${current ? ' actual' : ''}`}
                      to={`/school/${course.slug}/${lesson.slug}`}
                      aria-current={current ? 'page' : undefined}
                    >
                      {body}
                    </Link>
                  )}
                </li>
              );
            })}
          </ol>
        </section>
      ))}
    </aside>
  );
}
