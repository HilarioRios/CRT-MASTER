import { useEffect } from 'react';
import { ArrowIcon, LockIcon } from '../components/Icons.jsx';
import { LessonNavigation } from '../components/LessonNavigation.jsx';
import { LessonPlayer } from '../components/LessonPlayer.jsx';
import { LessonResources } from '../components/LessonResources.jsx';
import { LessonSidebar } from '../components/LessonSidebar.jsx';
import { LockedResource } from '../components/LockedResource.jsx';
import { Poster } from '../components/Poster.jsx';
import { Link } from '../components/Link.jsx';
import { SchoolLayout } from '../components/SchoolLayout.jsx';
import { brandConfig } from '../config/brand.js';
import { findModuleOf } from '../data/courses.js';
import { track } from '../lib/analytics.js';
import { lessonState, markCompleted, nextLesson, setLastLesson, setLessonPercent } from '../lib/progress.js';
import { updateCourseProgress, useCourseProgress } from '../lib/progressStore.js';
import { useResourceAccess } from '../lib/useResourceAccess.js';
import { fillTemplate } from '../lib/whatsapp.js';

// Cada cuántos puntos de avance del video se guarda el progreso.
const PERCENT_STEP = 5;

// Una clase sin bloqueo de equipo: siempre abierta.
const SIN_BLOQUEO = { id: 'sin-bloqueo', access: 'public' };

export function LessonPage({ course, lesson }) {
  const progress = useCourseProgress(course.id);
  const state = lessonState(course, progress, lesson.id);
  const locked = state === 'locked';
  const module = findModuleOf(course, lesson.id);

  // Bloqueo de equipo (clase 4): hasta que se canjea el código no hay video
  // ni recursos, y la clase no se puede completar.
  const gate = useResourceAccess(lesson.gate || SIN_BLOQUEO);
  // Una clase bloqueada solo se abre si el servidor entregó también su video.
  const gated = !locked && (gate.status !== 'unlocked' || Boolean(lesson.gate && !gate.video));
  const number = String(lesson.order).padStart(2, '0');

  useEffect(() => {
    if (!locked) updateCourseProgress(course.id, (p) => setLastLesson(p, lesson.id));
  }, [course.id, lesson.id, locked]);

  function complete(how) {
    if (state === 'completed') return;
    updateCourseProgress(course.id, (p) => markCompleted(p, lesson.id));
    track('clase_completada', { curso: course.id, clase: lesson.order, como: how });
  }

  function saveProgress(percent) {
    updateCourseProgress(course.id, (p) =>
      percent - (p.lessons[lesson.id]?.percent || 0) >= PERCENT_STEP ? setLessonPercent(p, lesson.id, percent) : p,
    );
  }

  const current = nextLesson(course, progress);

  return (
    <SchoolLayout course={course} withBottomBar={!locked}>
      <div className="school school-clase">
        <nav className="migas" aria-label="Dónde estás">
          <Link to={`/school/${course.slug}`}>{brandConfig.schoolName}</Link>
          <span aria-hidden="true">›</span>
          <span className="actual">{course.title} · Clase {lesson.order}</span>
        </nav>

        <div className="clase-layout">
          <div className="clase-columna">
            {locked ? (
              <div className="clase-cerrada">
                <span className="clase-cerrada-icono"><LockIcon size={20} /></span>
                <h1 className="display clase-h1">Clase {lesson.order}: {lesson.title}</h1>
                <p>Esta clase se abre cuando completes la anterior. Cada una se apoya en la que viene antes.</p>
                {current && (
                  <Link className="btn" to={`/school/${course.slug}/${current.slug}`}>
                    Ir a la clase {current.order} <ArrowIcon />
                  </Link>
                )}
              </div>
            ) : gate.loading ? (
              <div className="video video-cargando" aria-busy="true" />
            ) : gated ? (
              <>
                <div className="clase-bloqueada">
                  <div className="clase-bloqueada-media" aria-hidden="true">
                    {lesson.video.poster && <Poster src={lesson.video.poster} eager />}
                  </div>
                  <LockedResource
                    kind="clase"
                    typeLabel={`Clase ${number}${lesson.duration ? ` · ${lesson.duration}` : ''}`}
                    resource={{ ...lesson.gate, title: lesson.title }}
                    status={gate.status}
                    message={fillTemplate(brandConfig.whatsappLessonUnlockMessage, { n: lesson.order, curso: course.title })}
                    onRequest={() => {
                      gate.requestUnlock();
                      track('clase_desbloqueo_pedido', { curso: course.id, clase: lesson.order });
                    }}
                    onRedeem={async (code) => {
                      const result = await gate.redeem(code);
                      // Código válido pero sin video configurado en el servidor.
                      if (result.ok && !result.video) return { ok: false, reason: 'unavailable' };
                      if (result.ok) track('clase_desbloqueada', { curso: course.id, clase: lesson.order });
                      return result;
                    }}
                  />
                </div>
                <LessonNavigation course={course} lesson={lesson} progress={progress} />
              </>
            ) : (
              <>
                <LessonPlayer
                  lesson={lesson.gate ? { ...lesson, video: { ...lesson.video, loom: gate.video } } : lesson}
                  moduleTitle={course.modules.length > 1 ? module?.title : ''}
                  completed={state === 'completed'}
                  onPlay={() => track('clase_play', { curso: course.id, clase: lesson.order })}
                  onProgress={saveProgress}
                  onEnded={() => complete('video')}
                  onComplete={() => complete('boton')}
                />
                <LessonNavigation course={course} lesson={lesson} progress={progress} />
                <LessonResources course={course} lesson={lesson} />
              </>
            )}
          </div>
          <LessonSidebar course={course} progress={progress} currentLessonId={lesson.id} />
        </div>
      </div>
    </SchoolLayout>
  );
}
