import { ArrowIcon } from '../components/Icons.jsx';
import { Link } from '../components/Link.jsx';
import { SiteFooter, SiteHeader } from '../components/SiteChrome.jsx';
import { brandConfig } from '../config/brand.js';

export function NotFound() {
  return (
    <>
      <SiteHeader />
      <main className="main">
        <div className="curso">
          <section className="curso-hero">
            <p className="eyebrow">Página no encontrada</p>
            <h1 className="display curso-h1">Este enlace no existe</h1>
            <p className="curso-lede">Puede que la clase haya cambiado de lugar. Desde la School llegas a todo el contenido.</p>
            <Link className="btn no-encontrada-cta" to="/school">
              Ir a la {brandConfig.schoolName} <ArrowIcon />
            </Link>
          </section>
        </div>
      </main>
      <SiteFooter />
    </>
  );
}
