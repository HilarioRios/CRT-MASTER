import { Link } from '../components/Link.jsx';
import { SiteFooter, SiteHeader } from '../components/SiteChrome.jsx';
import { brandConfig } from '../config/brand.js';

// Datos legales pendientes de completar por el responsable de la marca.
const legal = {
  responsable: '[COMPLETAR: nombre o razón social del responsable]',
  pais: '[COMPLETAR: país]',
  email: '[COMPLETAR: email de contacto]',
  actualizada: '2 de octubre de 2026',
};

export function Privacy() {
  return (
    <>
      <SiteHeader />
      <main className="main">
        <article className="legal-doc">
          <p className="eyebrow">Legal</p>
          <h1 className="display legal-h1">Política de privacidad</h1>
          <p className="legal-fecha">Última actualización: {legal.actualizada}</p>
          <p>
            Esta política explica qué datos personales recogemos cuando usas esta página, para qué los usamos, con
            quién los compartimos y qué derechos tienes sobre ellos. Al marcar la casilla del formulario aceptas esta
            política.
          </p>

          <h2>1. Quién es el responsable de tus datos</h2>
          <p>
            El responsable del tratamiento de tus datos es <strong>{legal.responsable}</strong> ({legal.pais}), que
            opera la marca <strong>{brandConfig.name}</strong>. Para cualquier consulta sobre tus datos puedes
            escribir a {legal.email}.
          </p>

          <h2>2. Qué datos recogemos</h2>
          <ul>
            <li><strong>Los que escribes en el formulario:</strong> nombre, email, número de WhatsApp y país.</li>
            <li>
              <strong>Tus respuestas al cuestionario:</strong> cuánto tiempo llevas en el trading, qué te frena, a qué
              te dedicas y cuánto podrías invertir por mes en cuentas de fondeo. Las usamos para entender tu situación
              y recomendarte por dónde empezar.
            </li>
            <li>
              <strong>Datos de tu visita:</strong> desde qué anuncio o enlace llegaste (parámetros UTM), qué páginas
              viste y en qué pasos del cuestionario avanzaste, e identificadores de las cookies de Meta y de analítica
              (ver punto 8).
            </li>
            <li>
              <strong>Tu actividad en la página del curso:</strong> si la abriste, qué clases reprodujiste y qué
              materiales pediste. Tu avance en las clases se guarda en tu propio navegador.
            </li>
            <li>
              <strong>La prueba de tu consentimiento:</strong> el texto que aceptaste, la versión de esta política y la
              fecha.
            </li>
          </ul>
          <p>No te pedimos datos bancarios, de tarjetas ni de tus cuentas de trading.</p>

          <h2>3. Para qué los usamos</h2>
          <ul>
            <li>Enviarte el curso gratuito y sus materiales (clases y PDFs).</li>
            <li>
              Contactarte por WhatsApp, email o llamada con información relacionada con el curso, el trading y nuestros
              programas de formación, incluida una evaluación personalizada.
            </li>
            <li>Saber si recibiste y usaste el curso, para hacerte el seguimiento.</li>
            <li>Medir el rendimiento de nuestros anuncios y mejorar esta página.</li>
          </ul>

          <h2>4. Base legal</h2>
          <p>
            Tratamos tus datos <strong>con tu consentimiento</strong>, que das al marcar la casilla del formulario.
            Puedes retirarlo cuando quieras (ver punto 7), sin que eso afecte a lo que hicimos antes de que lo
            retiraras.
          </p>

          <h2>5. Con quién compartimos tus datos</h2>
          <p>
            <strong>No vendemos ni alquilamos tus datos.</strong> Solo los compartimos con los proveedores que
            necesitamos para funcionar, que los tratan por cuenta nuestra:
          </p>
          <ul>
            <li><strong>Netlify</strong> — alojamiento de esta página.</li>
            <li>
              <strong>Nuestro CRM y herramientas de automatización</strong> — donde guardamos tu contacto y gestionamos
              los mensajes que te enviamos.
            </li>
            <li>
              <strong>Meta Platforms</strong> — WhatsApp, para escribirte, y el Píxel de Meta, para medir nuestros
              anuncios en Facebook e Instagram.
            </li>
            <li><strong>PostHog</strong> — analítica de uso de la página.</li>
            <li>
              <strong>Loom (Atlassian) y YouTube (Google)</strong> — Loom aloja las clases del curso y YouTube la
              presentación de la página. Solo reciben datos cuando reproduces el video correspondiente.
            </li>
          </ul>
          <p>
            Algunos de estos proveedores están en Estados Unidos u otros países, por lo que tus datos pueden tratarse
            fuera de tu país, siempre con las garantías que exige la ley.
          </p>

          <h2>6. Cuánto tiempo los guardamos</h2>
          <p>
            Mientras sigas interesado en recibir nuestras comunicaciones. Si pides la baja o el borrado, eliminamos tus
            datos, salvo el registro mínimo que la ley nos obligue a conservar.
          </p>

          <h2>7. Tus derechos</h2>
          <p>Puedes, en cualquier momento:</p>
          <ul>
            <li>Pedir una copia de los datos que tenemos sobre ti.</li>
            <li>Corregirlos si están mal.</li>
            <li>Pedir que los borremos.</li>
            <li>Oponerte a que los usemos o pedir que limitemos su uso.</li>
            <li>Retirar tu consentimiento y dejar de recibir mensajes.</li>
          </ul>
          <p>
            Para ejercerlos, escríbenos a {legal.email}. Para dejar de recibir mensajes por WhatsApp también puedes
            responder <strong>BAJA</strong> en el chat. Si consideras que no respetamos tus derechos, puedes reclamar
            ante la autoridad de protección de datos de tu país.
          </p>

          <h2>8. Cookies y Píxel de Meta</h2>
          <p>
            Esta página usa el <strong>Píxel de Meta</strong> y la analítica de <strong>PostHog</strong>, que guardan
            cookies o identificadores en tu navegador. Con ellos, Meta puede asociar tu visita con tu cuenta de
            Facebook o Instagram para medir nuestros anuncios y mostrarte publicidad relacionada; nosotros recibimos
            solo estadísticas agregadas. Meta usa esos datos según su propia{' '}
            <a href="https://www.facebook.com/privacy/policy/" target="_blank" rel="noopener noreferrer">
              Política de privacidad
            </a>
            .
          </p>
          <p>
            Puedes bloquear o borrar las cookies desde la configuración de tu navegador, y decidir qué anuncios ves
            desde tus{' '}
            <a href="https://www.facebook.com/adpreferences" target="_blank" rel="noopener noreferrer">
              preferencias de anuncios de Meta
            </a>
            .
          </p>

          <h2>9. Menores de edad</h2>
          <p>
            Esta página y el curso están dirigidos a mayores de 18 años. No recogemos a sabiendas datos de menores; si
            detectamos que los recibimos, los borramos.
          </p>

          <h2>10. Seguridad</h2>
          <p>
            Usamos conexión cifrada (HTTPS) y limitamos el acceso a tus datos a las personas que los necesitan para
            atenderte.
          </p>

          <h2>11. Cambios en esta política</h2>
          <p>
            Si cambiamos esta política, publicaremos la versión nueva en esta página con su fecha. La versión que
            aceptaste queda registrada junto a tu consentimiento.
          </p>

          <p className="legal-volver">
            <Link to="/">← Volver al inicio</Link>
          </p>
        </article>
      </main>
      <SiteFooter />
    </>
  );
}
