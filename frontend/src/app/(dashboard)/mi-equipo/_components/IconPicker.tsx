"use client";

import { useEffect, useRef } from "react";

export const ICON_POOL = [
    "🤖", "🦾", "🧑‍💼", "👩‍💼", "🧑‍💻", "👩‍💻", "🧑‍🔬", "🧑‍🎨", "🧑‍🏫", "🧑‍⚕️", "🕵️", "🎯",
    "💼", "📊", "📈", "📉", "💰", "💳", "🏦", "🏢", "🤝", "📋", "🗂️", "📁",
    "📄", "📝", "📃", "🗒️", "📑", "🔖", "📌",
    "💻", "🖥️", "⚙️", "🔧", "🛠️", "🔌", "📡", "🖨️", "⌨️",
    "📧", "📨", "📬", "💬", "🗣️", "📞", "☎️", "📢", "📣",
    "🎬", "📸", "🎥", "🎨", "✏️", "🖌️",
    "⚖️", "🔐", "🛡️", "🔍", "📜", "✅",
    "📐", "🧮", "🔢", "📦", "🚀", "⭐", "🏆", "💡", "🔑",
    "👥", "👤", "🧑‍🤝‍🧑", "🎓", "🩺",
    "🚚", "🏭", "🌐", "🗺️", "📍",
];

export const COLOR_OPTIONS: { key: string; label: string; bg: string; border: string; swatch: string }[] = [
    { key: "violet",  label: "Violeta",  bg: "bg-violet-500/10",  border: "border-violet-500/20",  swatch: "bg-violet-500" },
    { key: "amber",   label: "Ámbar",    bg: "bg-amber-500/10",   border: "border-amber-500/20",   swatch: "bg-amber-500" },
    { key: "blue",    label: "Azul",     bg: "bg-blue-500/10",    border: "border-blue-500/20",    swatch: "bg-blue-500" },
    { key: "emerald", label: "Verde",    bg: "bg-emerald-500/10", border: "border-emerald-500/20", swatch: "bg-emerald-500" },
    { key: "rose",    label: "Rosa",     bg: "bg-rose-500/10",    border: "border-rose-500/20",    swatch: "bg-rose-500" },
    { key: "orange",  label: "Naranja",  bg: "bg-orange-500/10",  border: "border-orange-500/20",  swatch: "bg-orange-500" },
    { key: "cyan",    label: "Cian",     bg: "bg-cyan-500/10",    border: "border-cyan-500/20",    swatch: "bg-cyan-500" },
    { key: "pink",    label: "Rosa cl.", bg: "bg-pink-500/10",    border: "border-pink-500/20",    swatch: "bg-pink-500" },
    { key: "lime",    label: "Lima",     bg: "bg-lime-500/10",    border: "border-lime-500/20",    swatch: "bg-lime-500" },
    { key: "indigo",  label: "Índigo",   bg: "bg-indigo-500/10",  border: "border-indigo-500/20",  swatch: "bg-indigo-500" },
];

export function getAvatarClasses(color: string | null | undefined): string {
    const found = COLOR_OPTIONS.find(c => c.key === color);
    if (found) return `${found.bg} ${found.border}`;
    return "bg-violet-500/10 border-violet-500/20";
}

export function AppearancePicker({ currentIcon, currentColor, onSelect, onClose }: {
    currentIcon: string;
    currentColor: string | null;
    onSelect: (icon?: string, color?: string) => void;
    onClose: () => void;
}) {
    const ref = useRef<HTMLDivElement>(null);

    useEffect(() => {
        function handler(e: MouseEvent) {
            if (ref.current && !ref.current.contains(e.target as Node)) onClose();
        }
        document.addEventListener("mousedown", handler);
        return () => document.removeEventListener("mousedown", handler);
    }, [onClose]);

    return (
        <div ref={ref} className="absolute z-50 top-full left-0 mt-1 bg-card border border-border rounded-xl shadow-xl p-3 w-64">
            {/* Color */}
            <p className="text-[10px] text-muted-foreground mb-2 font-medium uppercase tracking-wider">Color del círculo</p>
            <div className="flex flex-wrap gap-1.5 mb-3">
                {COLOR_OPTIONS.map(c => (
                    <button key={c.key} onClick={() => onSelect(undefined, c.key)} title={c.label}
                        className={`w-6 h-6 rounded-full ${c.swatch} ring-offset-1 ring-offset-card transition-all ${currentColor === c.key ? "ring-2 ring-foreground scale-110" : "hover:scale-110"}`} />
                ))}
            </div>
            {/* Icon */}
            <p className="text-[10px] text-muted-foreground mb-2 font-medium uppercase tracking-wider">Icono</p>
            <div className="grid grid-cols-8 gap-1 max-h-40 overflow-y-auto">
                {ICON_POOL.map(icon => (
                    <button key={icon} onClick={() => { onSelect(icon, undefined); onClose(); }}
                        className={`text-lg p-1 rounded-lg hover:bg-accent transition-colors ${icon === currentIcon ? "bg-violet-500/20 ring-1 ring-violet-500/50" : ""}`}>
                        {icon}
                    </button>
                ))}
            </div>
        </div>
    );
}

/** @deprecated use AppearancePicker */
export function IconPicker({ current, onSelect, onClose }: { current: string; onSelect: (icon: string) => void; onClose: () => void }) {
    return <AppearancePicker currentIcon={current} currentColor={null} onSelect={(icon) => icon && onSelect(icon)} onClose={onClose} />;
}
