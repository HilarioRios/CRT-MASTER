// ══════════════════════════════════════════════════════════════════════
// CONTENIDO DE LA SCHOOL
//
//   courses → course → modules → lessons → resources
//
// Un video es { loom, youtube, file, poster }: `loom` acepta una URL de Loom,
// `youtube` un id o URL, `file` un mp4 propio y `poster` la miniatura.
//
// Recursos:
//   access: 'public'  → con `url` se abre/descarga; sin `url` se pide por WhatsApp.
//                       Un archivo propio va en /public/recursos y su `url`
//                       empieza con /recursos/.
//   access: 'team'    → bloqueado; lo desbloquea el equipo. NUNCA lleva `url`
//                       acá (este archivo es público): su link vive en el
//                       servidor, ver netlify/functions/recurso.js.
//
// Clase bloqueada por el equipo: `gate: { id, access: 'team' }`. Su video
// tampoco va acá: lo entrega el servidor junto con el recurso.
//   type: 'pdf' | 'checklist' | 'doc' | 'template' | 'indicator' | 'link' | 'file'
//
// Curso:
//   unlockMode: 'sequential' → cada clase se abre al completar la anterior.
//               'open'       → todas disponibles.
//
// En la School cada módulo es una pestaña (chip) y sus clases, la grilla.
// ══════════════════════════════════════════════════════════════════════

import crtPlaylist from './playlists/crt.json';

// LA CLASE 4 ESTÁ BLOQUEADA ENTERA: su video y su PDF. La persona le escribe
// a Gustavo por WhatsApp, recibe un código y con ese código se abre todo.
//
// Ni el video ni el link del PDF van acá (este archivo es público): viven en
// el servidor, en RESOURCE_VIDEO_CRT_C4 y RESOURCE_URL_CRT_C4.
const CRT_BLOQUEO_CLASE_4 = { id: 'crt-c4', access: 'team' };

// UN SOLO RECURSO POR CLASE: su PDF.
//
// Los PDF de Gustavo ("CRT MASTER") agrupan varios capítulos y hay 18
// capítulos para 14 videos, así que NO coinciden por número: se emparejaron
// por contenido (el tema de cada video con el tema de cada capítulo).
//
//   clase  tema del video                       PDF
//   1      cómo se mueve el mercado             cap 1
//   2      niveles clave                        cap 2 y 3
//   3      alineación de temporalidades         cap 4 y 5
//   4      tipos de rangos / modelos de CRT     cap 6, 7 y 8   (bloqueado)
//   5      escenarios semanales e intradía      cap 6, 7 y 8   (bloqueado)
//   6      estructura de mercado avanzada       cap 6, 7 y 8   (bloqueado)
//   7      trading de rangos                    cap 9, 10 y 11
//   8      apertura y cierre de velas (AMD)     cap 9, 10 y 11
//   9      divergencias SMT                     cap 12, 13 y 14
//   10     el tiempo: sesiones y horarios       cap 12, 13 y 14
//   11     gestión de riesgo                    cap 15 y 16
//   12     diario de trading                    cap 15 y 16
//   13     contexto del precio                  cap 17 y 18
//   14     modelo de entrada                    cap 17 y 18
//
// Los PDF públicos están en /public/recursos. El de los capítulos 6, 7 y 8
// es el de la clase bloqueada: NO está en /public ni lleva `url` acá; lo
// entrega el servidor con el código, y las clases 5 y 6 lo abren con ese
// mismo desbloqueo (`accessKey`).
const CRT_PDFS = [
  { clases: [1], capitulo: 'Capítulo 1', url: '/recursos/crt-master-cap-1.pdf' },
  { clases: [2], capitulo: 'Capítulos 2 y 3', url: '/recursos/crt-master-cap-2-3.pdf' },
  { clases: [3], capitulo: 'Capítulos 4 y 5', url: '/recursos/crt-master-cap-4-5.pdf' },
  { clases: [4, 5, 6], capitulo: 'Capítulos 6, 7 y 8', bloqueo: CRT_BLOQUEO_CLASE_4.id },
  { clases: [7, 8], capitulo: 'Capítulos 9, 10 y 11', url: '/recursos/crt-master-cap-9-10-11.pdf' },
  { clases: [9, 10], capitulo: 'Capítulos 12, 13 y 14', url: '/recursos/crt-master-cap-12-13-14.pdf' },
  { clases: [11, 12], capitulo: 'Capítulos 15 y 16', url: '/recursos/crt-master-cap-15-16.pdf' },
  { clases: [13, 14], capitulo: 'Capítulos 17 y 18', url: '/recursos/crt-master-cap-17-18.pdf' },
];

// Devuelve [] si una clase no tuviera PDF asignado.
const pdf = (lessonId, order) => {
  const file = CRT_PDFS.find((p) => p.clases.includes(order));
  if (!file) return [];
  const base = {
    id: `${lessonId}-pdf`,
    type: 'pdf',
    title: `PDF · ${file.capitulo}`,
    description: 'El material escrito de esta clase, para repasar lo que viste en el video.',
  };
  return [file.bloqueo ? { ...base, access: 'team', accessKey: file.bloqueo } : { ...base, access: 'public', url: file.url }];
};

// Las 14 clases del Curso CRT, en orden.
//
// El video, la duración y la miniatura original de cada una salen de
// src/data/playlists/crt.json (posición 1 = clase 1), que se genera con:
//
//   npm run import:playlist -- crt --private=4 <los 14 links, en orden>
//
// El título, la descripción y la dirección (slug) se escriben acá: así no
// cambian si se edita el título en YouTube.
//
// La clase 4 no expone su enlace en el JSON: el servidor lo entrega después
// de validar el código del equipo.
const CRT_CLASES = [
  ['el-punto-de-partida', 'Lo que casi nadie explica del trading', 'El punto de partida del curso: la idea sobre la que se apoya toda la estrategia CRT.'],
  ['key-levels', 'Key Levels: la pieza que le faltaba a CRT', 'Qué son los niveles clave y cómo se combinan con el rango para leer mejor el gráfico.'],
  ['temporalidades', 'Temporalidades en CRT', 'Qué temporalidad mirar para el rango y cuál para la entrada, sin confundirte entre una y otra.'],
  ['la-entrada', 'Cómo entrar con CRT', 'Dónde está la entrada y qué tiene que pasar en el gráfico antes de ejecutarla.'],
  ['bias-diario-y-semanal', 'Bias diario y semanal', 'Cómo leer la dirección del día y de la semana antes de buscar una operación.'],
  ['estructura-de-crt', 'La estructura de CRT', 'Cómo se arma la estructura del modelo, paso a paso.'],
  ['la-confirmacion', 'La confirmación de la entrada', 'Qué confirmación esperar antes de entrar, para ejecutar con un criterio claro.'],
  ['clase-8', 'Clase 8', 'Capítulo 8 del curso CRT.'],
  ['clase-9', 'Clase 9', 'Capítulo 9 del curso CRT.'],
  ['clase-10', 'Clase 10', 'Capítulo 10 del curso CRT.'],
  ['clase-11', 'Clase 11', 'Capítulo 11 del curso CRT.'],
  ['clase-12', 'Clase 12', 'Capítulo 12 del curso CRT.'],
  ['clase-13', 'Clase 13', 'Capítulo 13 del curso CRT.'],
  ['clase-14', 'Clase 14', 'Capítulo 14 del curso CRT, el último.'],
];

const crtLessons = CRT_CLASES.map(([slug, title, description], index) => {
  const order = index + 1;
  const id = `crt-c${order}`;
  const entry = crtPlaylist[index];
  const video = entry;
  return {
    id,
    slug,
    order,
    title,
    description,
    duration: video?.duration || '',
    locked: false,
    ...(order === 4 ? { gate: CRT_BLOQUEO_CLASE_4 } : {}),
    video: { loom: video?.loom || '', file: '', poster: video?.thumbnail || '' },
    resources: pdf(id, order),
  };
});

export const courses = [
  {
    id: 'crt',
    slug: 'crt',
    title: 'Curso CRT',
    description:
      'El curso completo de CRT, en orden: de la idea base a los niveles clave, las temporalidades, la entrada, el bias y la confirmación.',
    unlockMode: 'sequential',
    modules: [{ id: 'crt-clases', title: 'Curso CRT', lessons: crtLessons }],
  },
];

export function findCourse(slug) {
  return courses.find((c) => c.slug === slug) || null;
}

export function findLesson(course, slug) {
  for (const m of course.modules) {
    const found = m.lessons.find((l) => l.slug === slug);
    if (found) return found;
  }
  return null;
}

export function findModuleOf(course, lessonId) {
  return course.modules.find((m) => m.lessons.some((l) => l.id === lessonId)) || null;
}
