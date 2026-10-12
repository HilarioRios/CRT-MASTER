import { useState } from 'react';
import { LockIcon } from './Icons.jsx';
import { resourceType } from './ResourceCard.jsx';
import { WhatsAppCTA } from './WhatsAppCTA.jsx';

const ERRORS = {
  invalid_code: 'Ese código no es válido. Revísalo o pídele uno nuevo al equipo.',
  network: 'No pudimos conectar. Revisa tu conexión y vuelve a intentar.',
  not_configured: 'El desbloqueo con código todavía no está activo. El equipo te envía el recurso por WhatsApp.',
  unavailable: 'No pudimos abrir el recurso en este momento. Avísale al equipo por WhatsApp.',
};

const COPY = {
  recurso: {
    locked: 'Recurso bloqueado',
    aviso: 'Comunícate con mi equipo para desbloquear el recurso',
    requested: 'Ya le escribiste al equipo. Cuando validen tu avance te pasan un código: ingrésalo acá para abrir el recurso.',
  },
  clase: {
    locked: 'Clase bloqueada',
    aviso: 'Comunícate con mi equipo para desbloquear la clase',
    requested: 'Ya le escribiste al equipo. Cuando te pasen tu código, ingrésalo acá para abrir la clase y su material.',
  },
};

// Lo que entrega el equipo: un recurso o una clase entera (`kind`).
// Estados: 'locked' → 'unlock_requested'. Cuando pasa a 'unlocked' deja de
// mostrarse: acá nunca hay un link al documento ni al video.
export function LockedResource({ resource, status, message, onRequest, onRedeem, kind = 'recurso', typeLabel }) {
  const copy = COPY[kind];
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [hasCode, setHasCode] = useState(false);
  const requested = status === 'unlock_requested';
  const showForm = requested || hasCode;

  async function submit(event) {
    event.preventDefault();
    if (busy || !code.trim()) return;
    setBusy(true);
    setError('');
    const result = await onRedeem(code);
    setBusy(false);
    if (!result.ok) setError(ERRORS[result.reason] || ERRORS.network);
  }

  return (
    <div className={`recurso-bloqueado${requested ? ' pedido' : ''}`}>
      <div className="recurso-bloqueado-cabecera">
        <p className="recurso-bloqueado-rotulo">
          <LockIcon /> {requested ? 'Desbloqueo solicitado' : copy.locked}
        </p>
        {!requested && <p className="recurso-bloqueado-aviso">{copy.aviso}</p>}
      </div>
      <p className="recurso-tipo">{typeLabel || resourceType(resource.type).label}</p>
      <h4 className="recurso-bloqueado-titulo">{resource.title}</h4>
      {requested && <p className="recurso-bloqueado-texto">{copy.requested}</p>}

      {showForm && (
        <form className="codigo" onSubmit={submit} noValidate>
          <label className="campo-label" htmlFor={`codigo-${resource.id}`}>Código de acceso</label>
          <div className="codigo-fila">
            <input
              id={`codigo-${resource.id}`}
              className={error ? 'input mal' : 'input'}
              value={code}
              onChange={(event) => setCode(event.target.value)}
              placeholder="Tu código"
              autoComplete="off"
              autoCapitalize="none"
              spellCheck={false}
              aria-invalid={Boolean(error)}
            />
            <button type="submit" className="btn codigo-btn" disabled={busy || !code.trim()}>
              {busy ? 'Validando…' : 'Abrir'}
            </button>
          </div>
          {error && <p className="campo-error" role="alert">{error}</p>}
        </form>
      )}

      <WhatsAppCTA message={message} variant={requested ? 'outline' : 'solid'} onClick={onRequest}>
        {requested ? 'Volver a escribir al equipo' : 'Desbloquear con el equipo'}
      </WhatsAppCTA>
      {!showForm && (
        <button type="button" className="btn btn-codigo" onClick={() => setHasCode(true)}>
          Ya tengo el código
        </button>
      )}
    </div>
  );
}
