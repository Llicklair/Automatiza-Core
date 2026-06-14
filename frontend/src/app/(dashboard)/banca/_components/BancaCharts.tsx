"use client";

export function DonutChart({ segments }: { segments: { value: number; color: string }[] }) {
    const total = segments.reduce((s, x) => s + Math.abs(x.value), 0);
    if (total === 0) return null;

    const r = 52, cx = 60, cy = 60, stroke = 16;
    const circumference = 2 * Math.PI * r;

    // Offset acumulado de cada segmento (suma de los dash anteriores), calculado
    // de forma pura sin reasignar variables durante el render
    // (react-hooks/immutability): el offset de i es la suma de dashes [0..i).
    const dashes = segments.map((seg) => (Math.abs(seg.value) / total) * circumference);
    const arcs = segments.map((seg, i) => ({
        dash: dashes[i],
        gap: circumference - dashes[i],
        offset: dashes.slice(0, i).reduce((s, d) => s + d, 0),
        color: seg.color,
    }));

    return (
        <svg width={120} height={120} viewBox="0 0 120 120" className="rotate-[-90deg]">
            {arcs.map((arc, i) => (
                <circle key={i} cx={cx} cy={cy} r={r}
                    fill="none" stroke={arc.color} strokeWidth={stroke}
                    strokeDasharray={`${arc.dash} ${arc.gap}`}
                    strokeDashoffset={-arc.offset}
                    className="transition-all duration-700"
                />
            ))}
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
