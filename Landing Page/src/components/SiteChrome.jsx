import { brandConfig } from '../config/brand.js';
import { Link } from './Link.jsx';

export function Wordmark({ to = '/', label = brandConfig.name }) {
  return (
    <Link className="wordmark" to={to}>
      {brandConfig.logo ? <img className="wordmark-logo" src={brandConfig.logo} alt={label} /> : label}
    </Link>
  );
}

export function SiteHeader({ to = '/', label, children }) {
  return (
    <header className="header">
      <div className="header-inner">
        <Wordmark to={to} label={label} />
        {children && <div className="header-extra">{children}</div>}
      </div>
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="footer">
      <div className="footer-inner">
        <p>
          El trading de instrumentos financieros conlleva un alto riesgo y puede no ser adecuado para todas las
          personas: puedes perder parte o la totalidad del dinero que inviertes. Los resultados pasados no garantizan
          resultados futuros. Este contenido es educativo y no constituye asesoramiento financiero. Ningún resultado
          está garantizado.
        </p>
        <p>
          Este sitio no forma parte de Meta Platforms, Inc. ni está respaldado por Meta. Facebook e Instagram son
          marcas registradas de Meta Platforms, Inc.
        </p>
        <p className="footer-links">
          <Link to="/school">{brandConfig.schoolName}</Link>
          <span aria-hidden="true"> · </span>
          <Link to="/privacidad">Política de privacidad</Link>
          {brandConfig.instagramUrl && (
            <>
              <span aria-hidden="true"> · </span>
              <a href={brandConfig.instagramUrl} target="_blank" rel="noopener noreferrer">Instagram</a>
            </>
          )}
        </p>
        <p>
          © {new Date().getFullYear()} {brandConfig.name}. Todos los derechos reservados.
        </p>
      </div>
    </footer>
  );
}
