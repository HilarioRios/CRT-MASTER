import { useResourceAccess } from '../lib/useResourceAccess.js';
import { resolveVideo } from '../lib/video.js';
import { BrandCover } from './BrandCover.jsx';
import { CheckIcon, LockIcon, PlayIcon } from './Icons.jsx';
import { Link } from './Link.jsx';
import { Poster } from './Poster.jsx';

// Card de una clase en la grilla de la School: miniatura original, número,
// título, duración y estado (disponible / viendo / completada / bloqueada).
const SIN_BLOQUEO = { id: 'sin-bloqueo', access: 'public' };

export function LessonCard({ course, lesson, state, percent = 0, isNext = false }) {
  const video = resolveVideo(lesson.video);
  const number = String(lesson.order).padStart(2, '0');
  const completed = state === 'completed';
  // Bloqueo de equipo: se ve con candado hasta que se canjea el código.
  const gate = useResourceAccess(lesson.gate || SIN_BLOQUEO);
  const teamLocked = gate.status !== 'unlocked' || Boolean(lesson.gate && !gate.video);
  const locked = state === 'locked' || teamLocked;
  const pending = !lesson.gate && video.kind === 'pending';

  return (
    <Link className={`clase-card${locked ? ' cerrada' : ''}${isNext ? ' sigue' : ''}`} to={`/school/${course.slug}/${lesson.slug}`}>
      <div className="clase-card-media">
        {video.poster || lesson.video.poster ? (
          <Poster src={video.poster || lesson.video.poster} fallback={video.posterFallback} />
        ) : (
          <BrandCover label={number} />
        )}
        {locked && (
          <span className="clase-card-velo">
            <span className="clase-card-candado"><LockIcon size={16} /></span>
          </span>
        )}
        {!locked && !pending && (
          <span className="clase-card-play" aria-hidden="true"><PlayIcon size={18} /></span>
        )}
        {completed && (
          <span className="estado estado-ok"><CheckIcon size={10} /> Completada</span>
        )}
        {!completed && pending && <span className="estado">En grabación</span>}
        {lesson.duration && <span className="clase-card-duracion">{lesson.duration}</span>}
        {!completed && percent > 0 && (
          <span className="clase-card-avance" aria-hidden="true">
            <span style={{ width: `${percent}%` }} />
          </span>
        )}
      </div>
      <div className="clase-card-body">
        <p className="clase-card-rotulo">
          Clase {number}
          {state !== 'locked' && teamLocked ? ' · Con el equipo' : locked ? ' · Bloqueada' : isNext ? ' · Sigue esta' : ''}
        </p>
        <h2 className="clase-card-titulo">{lesson.title}</h2>
      </div>
    </Link>
  );
}
