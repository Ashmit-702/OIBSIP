"use client";

const ZONE_COLORS = ["#E2574C", "#E2574C", "#E0A63E", "#48C9B0", "#48C9B0"];

/**
 * Renders the entropy score (0-4) as an analog dial, like the tumbler
 * gauge on a physical vault, rather than a flat progress bar. The needle
 * rotates across a 140-degree arc; five etched ticks mark the score
 * bands (Very Weak -> Very Strong).
 */
export default function StrengthGauge({ score = 0, label = "-", entropyBits = 0 }) {
  const minAngle = -70;
  const maxAngle = 70;
  const angle = minAngle + (score / 4) * (maxAngle - minAngle);
  const color = ZONE_COLORS[score] ?? "#8B92A3";

  const ticks = [0, 1, 2, 3, 4].map((i) => {
    const a = minAngle + (i / 4) * (maxAngle - minAngle);
    return { angle: a, active: i <= score };
  });

  return (
    <div className="flex items-center gap-5">
      <svg viewBox="0 0 160 100" className="w-36 h-24 shrink-0" aria-hidden="true">
        <path
          d="M 20 90 A 70 70 0 0 1 140 90"
          fill="none"
          stroke="#282F40"
          strokeWidth="10"
          strokeLinecap="round"
        />
        {ticks.map((t, i) => {
          const rad = (t.angle * Math.PI) / 180;
          const x1 = 80 + 58 * Math.sin(rad);
          const y1 = 90 - 58 * Math.cos(rad);
          const x2 = 80 + 70 * Math.sin(rad);
          const y2 = 90 - 70 * Math.cos(rad);
          return (
            <line
              key={i}
              x1={x1}
              y1={y1}
              x2={x2}
              y2={y2}
              stroke={t.active ? color : "#3A4256"}
              strokeWidth="3"
              strokeLinecap="round"
              style={{ transition: "stroke 300ms ease" }}
            />
          );
        })}
        <g style={{ transform: `rotate(${angle}deg)`, transformOrigin: "80px 90px", transition: "transform 500ms cubic-bezier(0.34,1.56,0.64,1)" }}>
          <line x1="80" y1="90" x2="80" y2="34" stroke={color} strokeWidth="3" strokeLinecap="round" />
          <circle cx="80" cy="90" r="6" fill={color} />
        </g>
        <circle cx="80" cy="90" r="2.5" fill="#0C0F14" />
      </svg>

      <div className="min-w-0">
        <div className="font-mono text-xs uppercase tracking-widest text-muted mb-1">Strength</div>
        <div className="font-display text-2xl font-semibold" style={{ color }}>
          {label}
        </div>
        <div className="font-mono text-sm text-muted mt-0.5">{entropyBits} bits of entropy</div>
      </div>
    </div>
  );
}
