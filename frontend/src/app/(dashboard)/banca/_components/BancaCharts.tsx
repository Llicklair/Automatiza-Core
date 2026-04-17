"use client";

export function DonutChart({ segments }: { segments: { label: string; value: number; color: string }[] }) {
    const total = segments.reduce((s, x) => s + Math.abs(x.value), 0);
    if (total === 0) return null;

    const r = 52, cx = 60, cy = 60, stroke = 16;
    const circumference = 2 * Math.PI * r;
    let offset = 0;

    return (
        <svg width={120} height={120} viewBox="0 0 120 120" className="rotate-[-90deg]">
            {segments.map((seg, i) => {
                const pct = Math.abs(seg.value) / total;
                const dash = pct * circumference;
                const gap = circumference - dash;
                const el = (
                    <circle key={i} cx={cx} cy={cy} r={r}
                        fill="none" stroke={seg.color} strokeWidth={stroke}
                        strokeDasharray={`${dash} ${gap}`}
                        strokeDashoffset={-offset}
                        className="transition-all duration-700"
                    />
                );
                offset += dash;
                return el;
            })}
        </svg>
    );
}

export function BarSparkline({ values, color = "#6366f1" }: { values: number[]; color?: string }) {
    const max = Math.max(...values.map(Math.abs), 1);
    return (
        <div className="flex items-end gap-0.5 h-12">
            {values.map((v, i) => (
                <div key={i}
                    style={{ height: `${(Math.abs(v) / max) * 100}%`, backgroundColor: color, opacity: 0.7 + (i / values.length) * 0.3 }}
                    className="flex-1 rounded-sm transition-all duration-500"
                />
            ))}
        </div>
    );
}

export function AgentLoader({ label }: { label: string }) {
    return (
        <div className="flex flex-col items-center gap-4 py-12">
            <div className="w-10 h-10 rounded-full border-2 border-primary/30 border-t-primary animate-spin" />
            <p className="text-sm text-muted-foreground">{label}</p>
        </div>
    );
}
