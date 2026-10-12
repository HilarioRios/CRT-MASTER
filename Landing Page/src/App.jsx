import { useEffect, useRef } from 'react';
import { brandConfig } from './config/brand.js';
import { findCourse, findLesson } from './data/courses.js';
import { matchRoute, navigate, usePathname } from './lib/router.js';
import { Landing } from './pages/Landing.jsx';
import { LessonPage } from './pages/LessonPage.jsx';
import { NotFound } from './pages/NotFound.jsx';
import { Privacy } from './pages/Privacy.jsx';
import { SchoolHome } from './pages/SchoolHome.jsx';

const routes = [
  { name: 'landing', path: '/' },
  { name: 'school', path: '/school' },
  { name: 'course', path: '/school/:course' },
  { name: 'lesson', path: '/school/:course/:lesson' },
  { name: 'privacy', path: '/privacidad' },
  // Ruta de la web anterior: los links que ya circulan siguen funcionando.
  { name: 'legacyCourse', path: '/curso' },
];

function resolve(pathname) {
  const match = matchRoute(pathname, routes);
  if (!match) return { title: 'Página no encontrada', element: <NotFound /> };
  const { name, params } = match;

  if (name === 'landing') return { title: 'Estrategia CRT, paso a paso', element: <Landing /> };
  if (name === 'school') return { title: brandConfig.schoolName, element: <SchoolHome /> };
  if (name === 'privacy') return { title: 'Política de privacidad', element: <Privacy /> };
  if (name === 'legacyCourse') return { redirect: `/school/crt${window.location.search}` };

  const course = findCourse(params.course);
  if (!course) return { title: 'Página no encontrada', element: <NotFound /> };
  if (name === 'course') {
    const moduleId = new URLSearchParams(window.location.search).get('m');
    return { title: course.title, element: <SchoolHome course={course} moduleId={moduleId} /> };
  }

  const lesson = findLesson(course, params.lesson);
  if (!lesson) return { title: 'Página no encontrada', element: <NotFound /> };
  return {
    title: `Clase ${lesson.order}: ${lesson.title}`,
    element: <LessonPage course={course} lesson={lesson} />,
  };
}

export function App() {
  const pathname = usePathname();
  const { title, element, redirect } = resolve(pathname);

  const firstRender = useRef(true);

  useEffect(() => {
    if (redirect) navigate(redirect, { replace: true });
    else document.title = `${title} · ${brandConfig.name}`;
  }, [redirect, title]);

  // Al cambiar de página el foco va al título nuevo: quien navega con teclado
  // o lector de pantalla no queda perdido en el <body>.
  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    const heading = document.querySelector('main h1');
    if (heading) {
      heading.setAttribute('tabindex', '-1');
      heading.focus({ preventScroll: true });
    }
  }, [pathname]);

  return redirect ? null : element;
}
