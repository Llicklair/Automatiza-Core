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
] as const;
