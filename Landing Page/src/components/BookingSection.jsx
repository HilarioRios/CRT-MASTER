import { brandConfig } from '../config/brand.js';
import { track } from '../lib/analytics.js';
import { ArrowIcon } from './Icons.jsx';
import { WhatsAppCTA } from './WhatsAppCTA.jsx';

// El siguiente paso después de la VSL: agendar. El botón del calendario abre
// brandConfig.calendarUrl en una pestaña nueva; el otro, WhatsApp.
export function BookingSection() {
  const { calendarUrl } = brandConfig;
  return (
    <section className="agenda" aria-labelledby="agenda-titulo">
      <p className="eyebrow verde">Siguiente paso</p>
      <h2 className="display salida-h2" id="agenda-titulo">
        Agenda una llamada con el equipo
      </h2>
      <p className="salida-lede">
        Cuéntanos cómo estás operando hoy. Revisamos tu caso, te decimos qué corregir primero y por dónde seguir.
      </p>
      <div className="cta-caja agenda-caja">
        {calendarUrl && (
          <a className="btn" href={calendarUrl} target="_blank" rel="noopener noreferrer" onClick={() => track('agenda_calendario')}>
            Agendar en el calendario <ArrowIcon />
          </a>
        )}
        <WhatsAppCTA message={brandConfig.whatsappBookingMessage} onClick={() => track('agenda_whatsapp')}>
          Agendar por WhatsApp
        </WhatsAppCTA>
        <p className="card-nota">Elige el horario que te quede mejor o escríbenos y lo coordinamos.</p>
      </div>
    </section>
  );
}
