import { useState } from 'react';
import { BookingSection } from '../components/BookingSection.jsx';
import { DelayedReveal } from '../components/DelayedReveal.jsx';
import { ArrowIcon, LockIcon } from '../components/Icons.jsx';
import { Link } from '../components/Link.jsx';
import { SiteFooter, SiteHeader } from '../components/SiteChrome.jsx';
import { VideoPlayer } from '../components/VideoPlayer.jsx';
import { brandConfig } from '../config/brand.js';
import { courses } from '../data/courses.js';
import { track } from '../lib/analytics.js';
import { flattenLessons } from '../lib/progress.js';
import { readVslUnlocked, saveVslCompleted } from '../lib/vsl.js';

const { vsl } = brandConfig;
const totalClases = flattenLessons(courses[0]).length;

// Solo en desarrollo: /?agenda=1 abre la sección sin ver el video.
const devUnlock = import.meta.env.DEV && new URLSearchParams(window.location.search).has('agenda');

export function Landing() {
  const [unlocked, setUnlocked] = useState(() => devUnlock || readVslUnlocked(vsl.version));
  const [justUnlocked, setJustUnlocked] = useState(false);
  const [manual, setManual] = useState(false);

  function handleEnded() {
    if (unlocked) return;
    saveVslCompleted(vsl.version);
    setJustUnlocked(true);
    setUnlocked(true);
    track('vsl_completa');
  }

  return (
    <>
      <SiteHeader />
      <main className="main">
        <div className="shell">
          <div className="hero-top">
            <span className="pill">
              <span className="pill-punto" />
              Estrategia CRT · explicada por Gustavo
            </span>
          </div>
          <h1 className="display hero-h1">
            Opera con un plan claro: <br className="solo-desktop" />
            la estrategia CRT, paso a paso
          </h1>
          <p className="hero-sub">
            Mira el video completo. Gustavo te muestra cómo se lee el rango de una vela, dónde está la entrada y cómo
            se arma un plan para ejecutarlo sin improvisar.
          </p>

          <div className="vsl">
            <div className="vsl-marco">
              <VideoPlayer
                video={vsl}
                title="La estrategia CRT, paso a paso"
                pendingLabel="Video en preparación"
                onPlay={() => track('vsl_play')}
                onEnded={handleEnded}
                onTrackingUnavailable={() => setManual(true)}
              />
            </div>
            {/* El acceso al curso: bloqueado hasta que termina el video. */}
            <div className="vsl-acceso" aria-live="polite">
              {unlocked ? (
                <Link className={justUnlocked ? 'btn vsl-acceso-btn recien' : 'btn vsl-acceso-btn'} to="/school" onClick={() => track('landing_a_school')}>
                  Entrar al curso <ArrowIcon />
                </Link>
              ) : (
                <button type="button" className="btn vsl-acceso-btn" disabled>
                  <LockIcon size={15} /> Entrar al curso
                </button>
              )}
              {!unlocked && !manual && <p className="vsl-aviso">Se desbloquea cuando termines de ver el video.</p>}
            </div>
            {/* Solo si el navegador no deja saber cuándo termina el video. */}
            {!unlocked && manual && (
              <button type="button" className="btn btn-suave vsl-manual" onClick={handleEnded}>
                Ya vi el video completo
              </button>
            )}
          </div>

          <ul className="confianza">
            <li>
              <b>{totalClases} clases</b>
              <span>en video y en orden</span>
            </li>
            <li>
              <b>Material</b>
              <span>para repasar cada clase</span>
            </li>
            <li>
              <b>Equipo</b>
              <span>que te acompaña por WhatsApp</span>
            </li>
          </ul>

          <DelayedReveal open={unlocked} animate={justUnlocked}>
            <BookingSection />
          </DelayedReveal>

          <p className="legal">
            Contenido educativo. El trading implica riesgo y los resultados no están garantizados.
          </p>
        </div>
      </main>
      <SiteFooter />
    </>
  );
}
