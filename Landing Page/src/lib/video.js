// Un video se describe en los datos como { loom, youtube, file, poster }.
// `loom` acepta una URL pública de Loom, `youtube` el id o cualquier URL de
// YouTube y `file` un mp4/webm propio. Sin fuente, el video está "pendiente".

const ID = /^[\w-]{11}$/;
const LOOM_URL = /^https:\/\/(?:www\.)?loom\.com\/(?:share|embed)\/([a-f0-9]{32})(?:[/?#]|$)/i;

export function parseYoutubeId(input) {
  const value = String(input || '').trim();
  if (ID.test(value)) return value;
  const match = value.match(/(?:youtu\.be\/|[?&]v=|\/embed\/|\/shorts\/|\/live\/)([\w-]{11})/);
  return match ? match[1] : '';
}

export function parseLoomId(input) {
  return String(input || '').trim().match(LOOM_URL)?.[1] || '';
}

// maxresdefault es la miniatura original en 16:9; no todos los videos la
// tienen, por eso viaja junto a hqdefault (que existe siempre) como respaldo.
export function youtubePoster(id, quality = 'maxresdefault') {
  return `https://i.ytimg.com/vi/${id}/${quality}.jpg`;
}

export function resolveVideo(video) {
  const { loom, youtube, file, poster } = video || {};
  if (file) return { kind: 'file', src: file, poster: poster || '' };
  const loomId = parseLoomId(loom);
  if (loomId) {
    return {
      kind: 'loom',
      id: loomId,
      embedUrl: `https://www.loom.com/embed/${loomId}`,
      poster: poster || '',
    };
  }
  const id = parseYoutubeId(youtube);
  if (id) {
    return poster
      ? { kind: 'youtube', id, poster, posterFallback: '' }
      : { kind: 'youtube', id, poster: youtubePoster(id), posterFallback: youtubePoster(id, 'hqdefault') };
  }
  return { kind: 'pending' };
}
