// Portada de marca para una clase que todavía no tiene miniatura: el gráfico
// de velas con el rango CRT de la web de Gustavo.
const VELAS = [[14, 60, 68, 54, 74], [32, 68, 62, 56, 76], [50, 62, 74, 58, 80], [72, 32, 88, 26, 96], [96, 90, 78, 74, 110], [118, 78, 50, 46, 82], [140, 50, 30, 22, 54], [162, 30, 36, 20, 40]];

export function BrandCover({ label }) {
  return (
    <div className="portada" aria-hidden="true">
      <svg viewBox="0 0 240 124" preserveAspectRatio="xMidYMid slice">
        <rect x="58" y="26" width="182" height="70" fill="rgba(240,181,74,.06)" />
        <line x1="58" y1="26" x2="240" y2="26" stroke="#f0b54a" strokeWidth="1" strokeDasharray="3 3" />
        <line x1="58" y1="96" x2="240" y2="96" stroke="#f0b54a" strokeWidth="1" strokeDasharray="3 3" />
        <line x1="58" y1="61" x2="240" y2="61" stroke="rgba(240,181,74,.4)" strokeWidth="1" strokeDasharray="1 3" />
        {VELAS.map(([x, open, close, high, low]) => {
          const color = close < open ? '#26a69a' : '#ef5350';
          return (
            <g key={x}>
              <line x1={x} y1={high} x2={x} y2={low} stroke={color} strokeWidth="1.2" />
              <rect x={x - 5} y={Math.min(open, close)} width="10" height={Math.max(2, Math.abs(close - open))} fill={color} rx="1" />
            </g>
          );
        })}
      </svg>
      {label && <span className="portada-label">{label}</span>}
    </div>
  );
}
