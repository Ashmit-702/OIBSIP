"use client";

export default function Tabs({ tabs, active, onChange }) {
  return (
    <div className="flex gap-1 border-b border-line px-1" role="tablist">
      {tabs.map((t) => {
        const isActive = t.id === active;
        return (
          <button
            key={t.id}
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(t.id)}
            className={`relative px-5 py-3 font-display text-[15px] tracking-wide transition-colors ${
              isActive ? "text-brass-bright" : "text-muted hover:text-ink2"
            }`}
          >
            {t.label}
            {isActive && (
              <span className="absolute left-3 right-3 -bottom-px h-[2px] bg-brass rounded-full" />
            )}
          </button>
        );
      })}
    </div>
  );
}
