import { ArrowIcon } from '../components/Icons.jsx';
import { LessonCard } from '../components/LessonCard.jsx';
import { Link } from '../components/Link.jsx';
import { SchoolLayout } from '../components/SchoolLayout.jsx';
import { brandConfig } from '../config/brand.js';
import { courses } from '../data/courses.js';
import { completedCount, emptyProgress, flattenLessons, lessonState, nextLesson } from '../lib/progress.js';
import { useAllProgress } from '../lib/progressStore.js';
import { navigate } from '../lib/router.js';

const EMPTY = emptyProgress();

// Cada módulo de cada curso es una pestaña de la grilla.
const tabs = courses.flatMap((course) =>
  course.modules.map((module) => ({
    id: module.id,
    course,
    module,
    label: course.modules.length > 1 ? module.title : course.title,
  })),
);

// La home de la School: hero con el avance, filtros por curso y la grilla de
// clases. El curso elegido vive en la URL (/school/<curso>): se puede
// compartir y sobrevive a una recarga.
export function SchoolHome({ course = null, moduleId = null }) {
  const all = useAllProgress();
  const tab = tabs.find((t) => t.id === moduleId) || tabs.find((t) => t.course === course) || tabs[0];
  const progress = all[tab.course.id] || EMPTY;

  const total = flattenLessons(tab.course).length;
  const done = completedCount(tab.course, progress);
  const upNext = nextLesson(tab.course, progress);
  const cta = !upNext ? 'Repasar desde la clase 1' : done > 0 ? `Continuar · Clase ${upNext.order}` : 'Empezar por la clase 1';
  const ctaLesson = upNext || flattenLessons(tab.course)[0];

  return (
    <SchoolLayout course={tab.course}>
      <div className="school">
        <section className="hero-card">
          <span className="hero-rot">{brandConfig.schoolName} · Formación</span>
          <h1 className="display hero-card-h1">Tus clases</h1>
          <p>
            {tab.course.description}
            {tab.course.unlockMode === 'sequential' && (
              <>
                {' '}Las que están <b>bloqueadas</b> se abren a medida que completas la anterior.
              </>
            )}
          </p>
          <div className="hero-card-pie">
            {ctaLesson && (
              <Link className="btn hero-card-cta" to={`/school/${tab.course.slug}/${ctaLesson.slug}`}>
                {cta} <ArrowIcon />
              </Link>
            )}
            <span className="hero-card-cuenta">
              <b>{done}</b> de {total} clases completadas
            </span>
          </div>
        </section>

        {tabs.length > 1 && (
          <div className="chips" role="group" aria-label="Elegir curso">
            {tabs.map((t) => (
              <button
                key={t.id}
                type="button"
                aria-pressed={t.id === tab.id}
                className={t.id === tab.id ? 'chip is-on' : 'chip'}
                onClick={() => navigate(`/school/${t.course.slug}${t.course.modules.length > 1 ? `?m=${t.id}` : ''}`, { scroll: false })}
              >
                {t.label}
              </button>
            ))}
          </div>
        )}

        <div className="grid-clases">
          {tab.module.lessons.map((lesson) => (
            <LessonCard
              key={lesson.id}
              course={tab.course}
              lesson={lesson}
              state={lessonState(tab.course, progress, lesson.id)}
              percent={progress.lessons[lesson.id]?.percent || 0}
              isNext={done > 0 && upNext?.id === lesson.id}
            />
          ))}
        </div>
      </div>
    </SchoolLayout>
  );
}
