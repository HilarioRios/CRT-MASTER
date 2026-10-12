// ══════════════════════════════════════════════════════════════════════
// LA ÚNICA CONFIGURACIÓN DEL SITIO
//
// WhatsApp, calendario, redes, logo, foto y la VSL se cambian ACÁ y en
// ningún otro lado. Ningún componente repite un número ni una URL.
//
// Todo lo de este archivo termina en el navegador: acá NO va nada secreto
// (claves, tokens, links privados de documentos). Los links privados de los
// recursos bloqueados viven en variables de entorno del servidor: ver
// netlify/functions/recurso.js.
//
// Los valores también se pueden pisar por variable de entorno al hacer el
// build (útil en Netlify): VITE_WHATSAPP_NUMBER, VITE_CALENDAR_URL.
// ══════════════════════════════════════════════════════════════════════

const env = import.meta.env || {};

export const brandConfig = {
  name: 'Gustavo Trading',
  schoolName: 'CRT School',

  // Assets de marca. Vacío = se usa el wordmark en texto / no se muestra.
  // Poner el archivo en /public y la ruta acá (ej. '/brand/logo.svg').
  logo: '',
  portrait: '',
  favicon: '/favicon.svg',

  // WHATSAPP_NUMBER: solo dígitos con código de país, sin + ni espacios.
  whatsappNumber: env.VITE_WHATSAPP_NUMBER || '526632976748',
  whatsappDefaultMessage: 'Hola, estoy viendo el curso de CRT y quiero hablar con el equipo.',
  // WHATSAPP_UNLOCK_MESSAGE: {n} = número de clase, {curso} = nombre del curso.
  whatsappUnlockMessage: 'Hola, acabo de completar la clase {n} del {curso} y quiero desbloquear el recurso.',
  // Para desbloquear una clase entera (la 4): {n} = clase, {curso} = curso.
  whatsappLessonUnlockMessage: 'Hola, llegué a la clase {n} del {curso} y quiero desbloquearla.',
  whatsappBookingMessage: 'Hola, terminé de ver el video de CRT y quiero agendar una llamada con el equipo.',
  whatsappResourceMessage: 'Hola, estoy viendo el {curso}. ¿Me pasas "{recurso}" de la clase {n}: "{clase}"?',

  // CALENDAR_URL: link de la agenda. El botón "Agendar en el calendario" lo
  // abre en una pestaña nueva. PROVISORIO: reemplazar por el link real de
  // Gustavo (Google Calendar, Calendly, Cal.com...).
  calendarUrl: env.VITE_CALENDAR_URL || 'https://calendar.google.com/',
  instagramUrl: '',

  // La VSL de la landing. `youtube` acepta id o URL; `file` un mp4 propio en
  // /public. Si se cambia el video, subir `version` para que quien ya la vio
  // tenga que ver la nueva antes de que se abra la agenda.
  // PROVISORIO: video de prueba (un avance corto del canal de Gustavo).
  vsl: {
    youtube: 'J7N-3Vf9qBo',
    file: '',
    poster: '/thumbs/J7N-3Vf9qBo.jpg',
    version: 'vsl-prueba',
  },

  // Endpoint que canjea el código del equipo por el recurso bloqueado.
  resourceUnlockEndpoint: '/api/recurso',
};
