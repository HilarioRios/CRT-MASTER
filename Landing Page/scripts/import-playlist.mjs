// Importa una playlist de YouTube a la School: ids, títulos, duración y las
// miniaturas ORIGINALES descargadas a /public/thumbs.
//
//   npm run import:playlist -- <clave> <url de la playlist | urls de videos...>
//
//   npm run import:playlist -- crt "https://www.youtube.com/playlist?list=XXXX"
//   npm run import:playlist -- crt --reverse --private=4 "https://..."
//       --reverse     la playlist está de la última clase a la primera
//       --private=4   la clase 4 está bloqueada por el equipo
//
// Escribe src/data/playlists/<clave>.json. La clave "crt" es el Curso CRT
// (ver src/data/courses.js). No descarga los videos: se reproducen embebidos.
//
// Las clases se numeran por posición en la playlist: si después se reordena
// o se inserta un video, el progreso guardado y el recurso de la clase 4
// pasan a apuntar a otro video.
//
// Necesita yt-dlp (variable YT_DLP con la ruta, o tenerlo en el PATH).

import { execFileSync } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const args = process.argv.slice(2);
// --reverse: para playlists ordenadas de la última clase a la primera.
const reverse = args.includes('--reverse');
// --private=4 (o 4,6): clases bloqueadas por el equipo. Su id de YouTube NO
// se escribe en el JSON (que es público): se muestra en pantalla para
// cargarlo en el servidor como RESOURCE_VIDEO_<ID>.
const privadas = (args.find((arg) => arg.startsWith('--private='))?.split('=')[1] || '')
  .split(',')
  .map(Number)
  .filter(Boolean);
const [key, ...urls] = args.filter((arg) => !arg.startsWith('--'));

if (!key || urls.length === 0) {
  console.error('Uso: npm run import:playlist -- <clave> <url de playlist o urls de videos>');
  process.exit(1);
}

// La clave termina en el nombre del archivo: solo letras, números y guiones.
if (!/^[a-z0-9-]+$/.test(key)) {
  console.error(`Clave inválida: "${key}". Usa algo como "crt" (minúsculas, números y guiones).`);
  process.exit(1);
}

const ytDlp = process.env.YT_DLP || 'yt-dlp';
let raw;
try {
  raw = execFileSync(
    ytDlp,
    ['--ignore-errors', '--flat-playlist', '--print', '%(id)s\t%(duration_string)s\t%(title)s', ...urls],
    { encoding: 'utf8', maxBuffer: 32 * 1024 * 1024, stdio: ['ignore', 'pipe', 'ignore'] },
  );
} catch (error) {
  // Con videos privados yt-dlp termina con error pero igual lista el resto.
  if (typeof error.stdout !== 'string') {
    console.error(`No se pudo ejecutar yt-dlp (${error.code || error.message}). Instálalo o indica su ruta con YT_DLP=/ruta/a/yt-dlp.`);
    process.exit(1);
  }
  raw = error.stdout;
}

// Un video pasado por su link que yt-dlp no pudo leer está en PRIVADO en
// YouTube. Igual ocupa su lugar en el curso, marcado como no disponible:
// cuando se pase a "No listado" alcanza con volver a correr este script.
const videoId = (url) => url.match(/(?:youtu\.be\/|[?&]v=|\/embed\/|\/shorts\/|\/live\/)([\w-]{11})/)?.[1];
const leidos = new Set(raw.split('\n').map((line) => line.split('\t')[0]));
const ordenExplicito = urls.every(videoId);
if (ordenExplicito) {
  raw = urls
    .map((url) => {
      const id = videoId(url);
      return raw.split('\n').find((line) => line.startsWith(`${id}\t`)) || `${id}\t\tNO_DISPONIBLE`;
    })
    .join('\n');
} else if (urls.some((url) => videoId(url) && !leidos.has(videoId(url)))) {
  console.warn('Hay videos privados mezclados con una playlist: se omiten. Pasa todos los links de video, en orden, para conservar su lugar.');
}

async function downloadThumbnail(id, name = id) {
  for (const quality of ['maxresdefault', 'sddefault', 'hqdefault']) {
    const response = await fetch(`https://i.ytimg.com/vi/${id}/${quality}.jpg`).catch(() => null);
    if (!response?.ok) continue;
    const file = `/thumbs/${name}.jpg`;
    writeFileSync(join(root, 'public', file), Buffer.from(await response.arrayBuffer()));
    return { file, quality };
  }
  return { file: '', quality: 'sin miniatura' };
}

mkdirSync(join(root, 'public', 'thumbs'), { recursive: true });
mkdirSync(join(root, 'src', 'data', 'playlists'), { recursive: true });

const lines = raw.split('\n').filter(Boolean);
if (reverse) lines.reverse();

const entries = [];
for (const line of lines) {
  const [id, duration, ...title] = line.split('\t');
  if (!/^[\w-]{11}$/.test(id)) continue;
  if (title.join('') === 'NO_DISPONIBLE') {
    entries.push({ id, title: '', duration: '', thumbnail: '', available: false });
    console.warn(`${id}  PRIVADO en YouTube: queda como clase ${entries.length}, sin video por ahora`);
    continue;
  }
  // Videos privados o borrados: no se importan (correrían la numeración).
  if (/^(NA|\[(Private|Deleted) video\])$/i.test(title.join('').trim())) {
    console.warn(`${id}  OMITIDO (privado o no disponible)`);
    continue;
  }
  const order = entries.length + 1;
  const privada = privadas.includes(order);
  const thumb = await downloadThumbnail(id, privada ? `${key}-clase-${order}` : id);
  entries.push({
    id: privada ? '' : id,
    title: privada ? `Clase ${order} (video privado: se entrega con el código del equipo)` : title.join('\t').trim(),
    duration: duration === 'NA' ? '' : duration,
    thumbnail: thumb.file,
  });
  if (privada) console.log(`    ↑ clase ${order} PRIVADA: cargar su id en el servidor (no queda en el sitio)`);
  console.log(`${id}  ${thumb.quality.padEnd(14)} ${title.join(' ')}`);
}

if (entries.length === 0) {
  console.error('No se encontró ningún video: no se modificó nada.');
  process.exit(1);
}

const out = join(root, 'src', 'data', 'playlists', `${key}.json`);
writeFileSync(out, `${JSON.stringify(entries, null, 2)}\n`);
console.log(`\n${entries.length} videos → ${out}`);
