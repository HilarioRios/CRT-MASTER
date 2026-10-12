import { useEffect, useRef, useState } from 'react';
import { LOOM_ORIGIN, loomPlayerCommand, loomPlayerEvent, resolveVideo } from '../lib/video.js';
import { PlayIcon } from './Icons.jsx';
import { Poster } from './Poster.jsx';

// Reproductor único del sitio (VSL y clases).
//
//   video     { loom, youtube, file, poster }  — ver lib/video.js
//   onPlay    primera reproducción
//   onProgress(percent)  0–100 mientras avanza
//   onEnded   el video terminó DE VERDAD (evento del reproductor, no un timer)
//   onTrackingUnavailable  el video se ve, pero no se puede saber cuándo
//             termina (YouTube bloqueado por la red o una extensión)
//
// Antes de reproducir solo se carga el poster: ni el iframe ni el video.
// La excepción es Loom: su reproductor tarda varios segundos en llegar, así
// que se precarga oculto detrás del poster y al tocar ya está listo.

let youtubeApi;
const API_TIMEOUT_MS = 8000;

function loadYoutubeApi() {
  if (window.YT?.Player) return Promise.resolve(window.YT);
  if (!youtubeApi) {
    youtubeApi = new Promise((resolve, reject) => {
      const fail = () => {
        youtubeApi = undefined;
        reject(new Error('No se pudo cargar el reproductor de YouTube'));
      };
      const timeout = setTimeout(fail, API_TIMEOUT_MS);
      const previous = window.onYouTubeIframeAPIReady;
      window.onYouTubeIframeAPIReady = () => {
        clearTimeout(timeout);
        previous?.();
        resolve(window.YT);
      };
      const script = document.createElement('script');
      script.src = 'https://www.youtube.com/iframe_api';
      script.onerror = fail;
      document.head.appendChild(script);
    });
  }
  return youtubeApi;
}

function YoutubeFrame({ id, title, handlers }) {
  const mount = useRef(null);
  const [apiFailed, setApiFailed] = useState(false);

  useEffect(() => {
    let player;
    let timer;
    let cancelled = false;
    const stopTimer = () => clearInterval(timer);

    loadYoutubeApi()
      .then((YT) => {
        if (cancelled || !mount.current) return;
        // YT.Player reemplaza el nodo que recibe: se le da uno propio para
        // que React no pierda el suyo.
        const target = document.createElement('div');
        mount.current.appendChild(target);
        player = new YT.Player(target, {
          host: 'https://www.youtube-nocookie.com',
          videoId: id,
          playerVars: { autoplay: 1, rel: 0, playsinline: 1 },
          events: {
            onReady: (event) => {
              const frame = event.target.getIframe();
              frame.setAttribute('title', title);
              frame.focus({ preventScroll: true });
              event.target.playVideo();
            },
            onStateChange: (event) => {
              stopTimer();
              if (event.data === YT.PlayerState.PLAYING) {
                timer = setInterval(() => {
                  const duration = player.getDuration?.() || 0;
                  if (duration > 0) handlers.current.onProgress?.((player.getCurrentTime() / duration) * 100);
                }, 1000);
              }
              // Si desde la pantalla final se abrió otro video, su final no cuenta.
              const sameVideo = (player.getVideoData?.().video_id || id) === id;
              if (event.data === YT.PlayerState.ENDED && sameVideo) {
                handlers.current.onProgress?.(100);
                handlers.current.onEnded?.();
              }
            },
          },
        });
      })
      .catch(() => {
        if (cancelled) return;
        setApiFailed(true);
        handlers.current.onTrackingUnavailable?.();
      });

    return () => {
      cancelled = true;
      stopTimer();
      player?.destroy?.();
    };
  }, [id, title, handlers]);

  // Sin la API (bloqueador, red): el video se ve igual, pero el sitio no
  // puede saber cuándo termina.
  if (apiFailed) {
    return (
      <div className="video">
        <iframe
          src={`https://www.youtube-nocookie.com/embed/${id}?autoplay=1&rel=0&playsinline=1`}
          title={title}
          allow="autoplay; encrypted-media; picture-in-picture; fullscreen"
          allowFullScreen
        />
      </div>
    );
  }
  return <div className="video" ref={mount} />;
}

export function VideoPlayer({ video, title, onPlay, onProgress, onEnded, onTrackingUnavailable, pendingLabel = 'En grabación' }) {
  const source = resolveVideo(video);
  const [playing, setPlaying] = useState(false);
  const [loomReady, setLoomReady] = useState(false);
  const [loomMounted, setLoomMounted] = useState(false);
  const loomFrame = useRef(null);
  const loomReadyTimer = useRef();
  const wantsPlay = useRef(false);
  const handlers = useRef({});
  handlers.current = { onProgress, onEnded, onTrackingUnavailable };
  const isLoom = source.kind === 'loom';

  useEffect(() => () => clearTimeout(loomReadyTimer.current), []);

  const sendLoomPlay = () => loomFrame.current?.contentWindow?.postMessage(loomPlayerCommand('play'), LOOM_ORIGIN);
  const markLoomReady = () => {
    clearTimeout(loomReadyTimer.current);
    setLoomReady(true);
    if (wantsPlay.current) sendLoomPlay();
  };

  // Precarga el reproductor de Loom cuando el navegador queda libre, salvo
  // que la persona haya pedido ahorrar datos.
  useEffect(() => {
    if (!isLoom || loomMounted || navigator.connection?.saveData) return undefined;
    if (window.requestIdleCallback) {
      const handle = window.requestIdleCallback(() => setLoomMounted(true), { timeout: 1500 });
      return () => window.cancelIdleCallback(handle);
    }
    const handle = setTimeout(() => setLoomMounted(true), 600);
    return () => clearTimeout(handle);
  }, [isLoom, loomMounted]);

  // Loom avisa por postMessage cuando su reproductor ya se puede usar.
  useEffect(() => {
    if (!isLoom) return undefined;
    const onMessage = (event) => {
      if (event.source !== loomFrame.current?.contentWindow) return;
      if (loomPlayerEvent(event) === 'ready') markLoomReady();
    };
    window.addEventListener('message', onMessage);
    return () => window.removeEventListener('message', onMessage);
  }, [isLoom]);

  if (source.kind === 'pending') {
    return (
      <div className="video video-pendiente">
        <span>{pendingLabel}</span>
      </div>
    );
  }

  if (source.kind === 'file') {
    return (
      <div className="video">
        <video
          src={source.src}
          poster={source.poster || undefined}
          controls
          playsInline
          preload="none"
          title={title}
          onPlay={() => {
            if (!playing) {
              setPlaying(true);
              onPlay?.();
            }
          }}
          onTimeUpdate={(event) => {
            const { currentTime, duration } = event.currentTarget;
            if (duration > 0) onProgress?.((currentTime / duration) * 100);
          }}
          onEnded={() => onEnded?.()}
        />
      </div>
    );
  }

  if (isLoom) {
    const visible = playing && loomReady;
    return (
      <div className={`video video-loom ${visible ? 'video-loom-listo' : ''}`} aria-busy={playing && !loomReady}>
        {loomMounted && (
          <iframe
            ref={loomFrame}
            className="video-loom-frame"
            src={source.embedUrl}
            title={title}
            allow="autoplay; fullscreen; picture-in-picture"
            allowFullScreen
            tabIndex={visible ? 0 : -1}
            aria-hidden={!visible}
            onLoad={() => {
              // Respaldo por si el aviso de "listo" de Loom no llega.
              clearTimeout(loomReadyTimer.current);
              loomReadyTimer.current = setTimeout(markLoomReady, 2500);
            }}
          />
        )}
        {!visible && (
          <button
            type="button"
            className="video-poster video-loom-tapa"
            aria-label={`Reproducir: ${title}`}
            disabled={playing}
            onClick={() => {
              wantsPlay.current = true;
              setPlaying(true);
              setLoomMounted(true);
              onPlay?.();
              if (loomReady) sendLoomPlay();
            }}
          >
            <Poster className="video-poster-img" src={source.poster} fallback={source.posterFallback} eager />
            {playing ? (
              <span className="video-loom-estado" role="status">
                <span className="video-loom-spinner" aria-hidden="true" />
                Cargando video…
              </span>
            ) : (
              <span className="video-play" aria-hidden="true">
                <PlayIcon />
              </span>
            )}
          </button>
        )}
      </div>
    );
  }

  if (playing) return <YoutubeFrame id={source.id} title={title} handlers={handlers} />;

  return (
    <button
      type="button"
      className="video video-poster"
      aria-label={`Reproducir: ${title}`}
      onClick={() => {
        setPlaying(true);
        onPlay?.();
      }}
    >
      <Poster className="video-poster-img" src={source.poster} fallback={source.posterFallback} eager />
      <span className="video-play" aria-hidden="true">
        <PlayIcon />
      </span>
    </button>
  );
}
