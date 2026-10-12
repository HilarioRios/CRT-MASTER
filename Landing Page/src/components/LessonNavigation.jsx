import { adjacentLessons, lessonState } from '../lib/progress.js';
import { ArrowIcon, LockIcon } from './Icons.jsx';
import { Link } from './Link.jsx';

// Anterior / siguiente. En mobile queda fija abajo: pasar de clase es
// siempre un toque, sin buscar el listado.
export function LessonNavigation({ course, lesson, progress }) {
  const { prev, next } = adjacentLessons(course, lesson.id);
  const nextLocked = next && lessonState(course, progress, next.id) === 'locked';
  const highlight = lessonState(course, progress, lesson.id) === 'completed';

  return (
    <nav className="clase-nav" aria-label="Navegación entre clases">
      {prev ? (
        <Link className="btn btn-suave" to={`/school/${course.slug}/${prev.slug}`}>
          <ArrowIcon back /> Anterior
        </Link>
      ) : (
        <button type="button" className="btn btn-suave" disabled>
          <ArrowIcon back /> Anterior
        </button>
      )}

      {!next ? (
        <Link className="btn btn-suave" to={`/school/${course.slug}`}>
          Todas las clases
        </Link>
      ) : nextLocked ? (
        <button type="button" className="btn btn-suave" disabled>
          <LockIcon /> Completa esta clase
        </button>
      ) : (
        <Link className={highlight ? 'btn' : 'btn btn-suave'} to={`/school/${course.slug}/${next.slug}`}>
          Siguiente <ArrowIcon />
        </Link>
      )}
    </nav>
  );
}
