// Progreso de un curso. variant 'bar' (cards, sidebar) o 'ring' (header).
export function CourseProgress({ percent, variant = 'bar', label = 'Progreso del curso' }) {
  if (variant === 'ring') {
    const r = 15;
    const length = 2 * Math.PI * r;
    return (
      <span className="anillo" role="img" aria-label={`${label}: ${percent}%`}>
        <svg width="38" height="38" viewBox="0 0 38 38" aria-hidden="true">
          <circle cx="19" cy="19" r={r} fill="none" stroke="rgba(255,255,255,.12)" strokeWidth="3" />
          {percent > 0 && <circle
            className="anillo-arco"
            cx="19"
            cy="19"
            r={r}
            fill="none"
            stroke="var(--acento-suave)"
            strokeWidth="3"
            strokeLinecap="round"
            strokeDasharray={`${(percent / 100) * length} ${length}`}
            transform="rotate(-90 19 19)"
          />}
        </svg>
        <span className="anillo-cifra">{percent}%</span>
      </span>
    );
  }
  return (
    <div className="progreso progreso-curso" role="progressbar" aria-valuenow={percent} aria-valuemin={0} aria-valuemax={100} aria-label={label}>
      <div className="progreso-barra" style={{ width: `${percent}%` }} />
    </div>
  );
}
