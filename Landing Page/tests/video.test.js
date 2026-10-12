import { describe, it, expect } from 'vitest';
import { loomPlayerCommand, loomPlayerEvent, parseLoomId, parseYoutubeId, resolveVideo } from '../src/lib/video.js';
import { isVslUnlocked } from '../src/lib/vsl.js';

describe('parseYoutubeId', () => {
  it('acepta un id suelto', () => {
    expect(parseYoutubeId('Cufyhpcqq6c')).toBe('Cufyhpcqq6c');
  });

  it('acepta las formas habituales de URL', () => {
    expect(parseYoutubeId('https://www.youtube.com/watch?v=Cufyhpcqq6c&t=10s')).toBe('Cufyhpcqq6c');
    expect(parseYoutubeId('https://youtu.be/Cufyhpcqq6c?si=abc')).toBe('Cufyhpcqq6c');
    expect(parseYoutubeId('https://www.youtube.com/embed/Cufyhpcqq6c')).toBe('Cufyhpcqq6c');
    expect(parseYoutubeId('https://www.youtube.com/shorts/Cufyhpcqq6c')).toBe('Cufyhpcqq6c');
  });

  it('devuelve cadena vacía si no hay id', () => {
    expect(parseYoutubeId('')).toBe('');
    expect(parseYoutubeId(undefined)).toBe('');
    expect(parseYoutubeId('https://example.com/video')).toBe('');
  });
});

describe('parseLoomId', () => {
  const id = '32a18566e0b84bbb8ac4d93b7d7f2db1';

  it('acepta enlaces compartidos y embebidos de Loom', () => {
    expect(parseLoomId(`https://www.loom.com/share/${id}`)).toBe(id);
    expect(parseLoomId(`https://www.loom.com/embed/${id}`)).toBe(id);
  });

  it('rechaza enlaces que no pertenecen a Loom', () => {
    expect(parseLoomId(`https://example.com/share/${id}`)).toBe('');
    expect(parseLoomId('')).toBe('');
  });
});

describe('resolveVideo', () => {
  it('sin fuente el video queda pendiente', () => {
    expect(resolveVideo({ youtube: '', file: '' })).toEqual({ kind: 'pending' });
    expect(resolveVideo(undefined)).toEqual({ kind: 'pending' });
  });

  it('con YouTube usa su miniatura original en alta, con la estándar como respaldo', () => {
    expect(resolveVideo({ youtube: 'https://youtu.be/Cufyhpcqq6c' })).toEqual({
      kind: 'youtube',
      id: 'Cufyhpcqq6c',
      poster: 'https://i.ytimg.com/vi/Cufyhpcqq6c/maxresdefault.jpg',
      posterFallback: 'https://i.ytimg.com/vi/Cufyhpcqq6c/hqdefault.jpg',
    });
  });

  it('un poster propio tiene prioridad sobre la miniatura de YouTube y no lleva respaldo', () => {
    const video = resolveVideo({ youtube: 'Cufyhpcqq6c', poster: '/thumbs/c1.jpg' });
    expect(video.poster).toBe('/thumbs/c1.jpg');
    expect(video.posterFallback).toBe('');
  });

  it('con archivo propio usa el reproductor nativo', () => {
    expect(resolveVideo({ file: '/videos/vsl.mp4', poster: '/p.jpg' })).toEqual({
      kind: 'file',
      src: '/videos/vsl.mp4',
      poster: '/p.jpg',
    });
  });

  it('con Loom produce una fuente embebida y conserva el poster', () => {
    const id = '32a18566e0b84bbb8ac4d93b7d7f2db1';
    expect(resolveVideo({ loom: `https://www.loom.com/share/${id}`, poster: '/p.gif' })).toEqual({
      kind: 'loom',
      id,
      embedUrl: `https://www.loom.com/embed/${id}?hide_owner=true&hide_share=true&hide_title=true&hideEmbedTopBar=true`,
      poster: '/p.gif',
    });
  });

  it('el embed de Loom oculta dueño, compartir, título y barra superior', () => {
    const { embedUrl } = resolveVideo({ loom: 'https://www.loom.com/share/32a18566e0b84bbb8ac4d93b7d7f2db1' });
    const params = new URL(embedUrl).searchParams;
    expect(params.get('hide_owner')).toBe('true');
    expect(params.get('hide_share')).toBe('true');
    expect(params.get('hide_title')).toBe('true');
    expect(params.get('hideEmbedTopBar')).toBe('true');
  });
});

describe('loomPlayerEvent', () => {
  const ready = JSON.stringify({ context: 'player.js', version: '0.0.11', event: 'ready', value: {} });

  it('reconoce el aviso de que el reproductor de Loom está listo', () => {
    expect(loomPlayerEvent({ origin: 'https://www.loom.com', data: ready })).toBe('ready');
  });

  it('acepta el mensaje como objeto además de como texto', () => {
    expect(loomPlayerEvent({ origin: 'https://www.loom.com', data: { context: 'player.js', event: 'play' } })).toBe('play');
  });

  it('ignora mensajes de otro origen', () => {
    expect(loomPlayerEvent({ origin: 'https://evil.example', data: ready })).toBe('');
  });

  it('ignora mensajes que no son del reproductor o no se pueden leer', () => {
    expect(loomPlayerEvent({ origin: 'https://www.loom.com', data: '{no es json' })).toBe('');
    expect(loomPlayerEvent({ origin: 'https://www.loom.com', data: JSON.stringify({ context: 'otro', event: 'ready' }) })).toBe('');
    expect(loomPlayerEvent({ origin: 'https://www.loom.com', data: null })).toBe('');
  });
});

describe('loomPlayerCommand', () => {
  it('arma la orden de reproducir en el formato que entiende Loom', () => {
    expect(JSON.parse(loomPlayerCommand('play'))).toEqual({ context: 'player.js', version: '0.0.11', method: 'play' });
  });
});

describe('isVslUnlocked', () => {
  it('está bloqueada si nunca terminó el video', () => {
    expect(isVslUnlocked(null, 'v1')).toBe(false);
  });

  it('queda desbloqueada si terminó esta versión del video', () => {
    expect(isVslUnlocked({ completed: true, version: 'v1' }, 'v1')).toBe(true);
  });

  it('si cambia la versión del video hay que volver a verlo', () => {
    expect(isVslUnlocked({ completed: true, version: 'v1' }, 'v2')).toBe(false);
  });
});
