// ── Plataformas ────────────────────────────────────────────────────────────────

export const PLATFORMS = [
    {
        id: "instagram",
        name: "Instagram",
        limit: 2200,
        colorClass: "text-pink-400 bg-pink-500/10 border-pink-500/20",
        iconBg: "bg-pink-500/15",
    },
    {
        id: "facebook",
        name: "Facebook",
        limit: 63206,
        colorClass: "text-blue-400 bg-blue-500/10 border-blue-500/20",
        iconBg: "bg-blue-500/15",
    },
    {
        id: "linkedin",
        name: "LinkedIn",
        limit: 3000,
        colorClass: "text-sky-400 bg-sky-500/10 border-sky-500/20",
        iconBg: "bg-sky-500/15",
    },
    {
        id: "twitter",
        name: "X (Twitter)",
        limit: 280,
        colorClass: "text-zinc-300 bg-zinc-500/10 border-zinc-500/20",
        iconBg: "bg-zinc-500/15",
    },
    {
        id: "tiktok",
        name: "TikTok",
        limit: 2200,
        colorClass: "text-zinc-200 bg-zinc-700/20 border-zinc-500/20",
        iconBg: "bg-zinc-700/30",
    },
    {
        id: "youtube",
        name: "YouTube",
        limit: 5000,
        colorClass: "text-red-400 bg-red-500/10 border-red-500/20",
        iconBg: "bg-red-500/15",
    },
    {
        id: "threads",
        name: "Threads",
        limit: 500,
        colorClass: "text-zinc-200 bg-zinc-700/20 border-zinc-500/20",
        iconBg: "bg-zinc-700/30",
    },
    {
        id: "pinterest",
        name: "Pinterest",
        limit: 500,
        colorClass: "text-red-400 bg-red-500/10 border-red-500/20",
        iconBg: "bg-red-500/15",
    },
    {
        id: "reddit",
        name: "Reddit",
        limit: 40000,
        colorClass: "text-orange-400 bg-orange-500/10 border-orange-500/20",
        iconBg: "bg-orange-500/15",
    },
    {
        id: "googlebusiness",
        name: "Google Business",
        limit: 1500,
        colorClass: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
        iconBg: "bg-emerald-500/15",
    },
] as const;

// Con Zernio (BYO) ya no hay apps OAuth propias por plataforma: Zernio es socio
// oficial y gestiona los permisos/revisiones. Por eso no se oculta ninguna red.
export const HIDDEN_PLATFORM_IDS = new Set<string>([]);

// Plataformas que el usuario puede conectar (excluye las ocultas). PLATFORMS se
// mantiene completa a propósito para que las búsquedas de visualización
// (icono/nombre/color) sigan resolviendo cualquier post existente sin romper.
export const CONNECTABLE_PLATFORMS = PLATFORMS.filter((p) => !HIDDEN_PLATFORM_IDS.has(p.id));
