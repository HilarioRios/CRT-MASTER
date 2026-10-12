import { brandConfig } from '../config/brand.js';
import { courses } from '../data/courses.js';
import { completedCount, coursePercent, emptyProgress, flattenLessons } from '../lib/progress.js';
import { useAllProgress } from '../lib/progressStore.js';
import { CourseProgress } from './CourseProgress.jsx';
import { SiteFooter, SiteHeader } from './SiteChrome.jsx';
import { WhatsAppCTA } from './WhatsAppCTA.jsx';

const EMPTY = emptyProgress();

function overallPercent(all) {
  let done = 0;
  let total = 0;
  for (const course of courses) {
    done += completedCount(course, all[course.id] || EMPTY);
    total += flattenLessons(course).length;
  }
  return total ? Math.round((done / total) * 100) : 0;
}

// Marco de todas las páginas de la School: header con el progreso (el del
// curso si se está dentro de uno; el general en la home), footer y la
// burbuja de WhatsApp.
export function SchoolLayout({ children, course = null, withBottomBar = false }) {
  const all = useAllProgress();
  const percent = course ? coursePercent(course, all[course.id] || EMPTY) : overallPercent(all);
  return (
    <>
      <SiteHeader to="/school">
        <span className="header-school">{brandConfig.schoolName}</span>
        <CourseProgress variant="ring" percent={percent} label={course ? `Tu progreso en ${course.title}` : 'Tu progreso en la School'} />
      </SiteHeader>
      <main className={withBottomBar ? 'main main-school con-barra' : 'main main-school'}>{children}</main>
      <SiteFooter />
      <WhatsAppCTA variant="fab" className={withBottomBar ? 'sobre-barra' : ''}>
        Hablar con el equipo
      </WhatsAppCTA>
    </>
  );
}
