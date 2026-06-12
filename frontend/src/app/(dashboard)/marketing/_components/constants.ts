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

// LinkedIn oculto temporalmente: dar de alta su app requiere una Company Page de
// LinkedIn, y crear la página exige un mínimo de conexiones (bloqueo del lado de
// LinkedIn, no del producto). El backend ya lo soporta vía proxy. Para reactivar:
// quita "linkedin" de HIDDEN_PLATFORM_IDS y pon LINKEDIN_CLIENT_ID/SECRET en Render.
export const HIDDEN_PLATFORM_IDS = new Set<string>(["linkedin"]);

// Plataformas que el usuario puede conectar (excluye las ocultas). PLATFORMS se
// mantiene completa a propósito para que las búsquedas de visualización
// (icono/nombre/color) sigan resolviendo cualquier post existente sin romper.
export const CONNECTABLE_PLATFORMS = PLATFORMS.filter((p) => !HIDDEN_PLATFORM_IDS.has(p.id));
