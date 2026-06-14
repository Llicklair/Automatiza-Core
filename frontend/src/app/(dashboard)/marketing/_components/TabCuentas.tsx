"use client";

import { useState, useEffect, useCallback } from "react";
import { Loader2, CheckCircle2, AlertCircle, AlertTriangle, Plus } from "lucide-react";
import { marketingApi, SocialAccount, MarketingConfigStatus } from "@/lib/api/marketing";
import { PLATFORM_ICONS } from "@/components/ui/social-icons";
import { CONNECTABLE_PLATFORMS } from "./constants";

// ── Tab: Cuentas ───────────────────────────────────────────────────────────────

// Estado de caducidad del token de una cuenta conectada. null = sin aviso (sin
// fecha conocida o caduca lejos). Meta/LinkedIn duran ~60 días; avisamos a 7.
function tokenStatus(expiresAt: string | null): { level: "soon" | "expired"; label: string } | null {
    if (!expiresAt) return null;
    const ms = new Date(expiresAt).getTime() - Date.now();
    if (Number.isNaN(ms)) return null;
    if (ms <= 0) return { level: "expired", label: "Token caducado — reconecta" };
    const days = Math.ceil(ms / 86_400_000);
    if (days <= 7) return { level: "soon", label: `Caduca en ${days} día${days === 1 ? "" : "s"} — reconecta` };
    return null;
}

export function TabCuentas() {
    const [accounts, setAccounts] = useState<SocialAccount[]>([]);
    const [config, setConfig] = useState<MarketingConfigStatus | null>(null);
    const [loading, setLoading] = useState(true);
    const [connecting, setConnecting] = useState<string | null>(null);
    const [connectError, setConnectError] = useState<string | null>(null);

    const load = useCallback(async () => {
        try {
            const data = await marketingApi.accounts.list();
            setAccounts(data);
        } catch {
            // sin cuentas aún
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { load(); }, [load]);

    useEffect(() => {
        marketingApi.configStatus().then(setConfig).catch(() => setConfig(null));
    }, []);

    // Refresca cuando el popup OAuth cierra con éxito (postMessage cross-origin)
    useEffect(() => {
        const handler = (e: MessageEvent) => {
            if (e.data?.type === "oauth-complete") load();
        };
        window.addEventListener("message", handler);
        return () => window.removeEventListener("message", handler);
    }, [load]);

    const connect = async (platform: string) => {
        setConnecting(platform);
        setConnectError(null);
        try {
            const { auth_url } = await marketingApi.accounts.connect(platform);
            // En Electron los OAuth de redes sociales abren en el browser del sistema.
            // window.open devuelve null pero el browser real maneja el flujo.
            // En Electron: IPC → shell.openExternal (100% fiable). En browser: window.open normal.
            const eAPI = (window as typeof window & { electronAPI?: { openExternal?: (u: string) => Promise<void> } }).electronAPI;
            if (eAPI?.openExternal) {
                await eAPI.openExternal(auth_url);
            } else {
                window.open(auth_url, "_blank", "width=600,height=700");
            }
            // Polling hasta 60s para detectar cuando el callback llegue al backend
            const before = accounts.map((a) => a.id);
            let attempts = 0;
            const iv = setInterval(async () => {
                attempts++;
                try {
                    const fresh = await marketingApi.accounts.list();
                    if (fresh.some((a) => !before.includes(a.id))) {
                        setAccounts(fresh);
                        clearInterval(iv);
                    }
                } catch { /* ignore */ }
                if (attempts >= 30) clearInterval(iv);
            }, 2000);
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : "Error al conectar";
            setConnectError(msg);
        } finally {
            setConnecting(null);
        }
    };

    const disconnect = async (id: string) => {
        try {
            await marketingApi.accounts.disconnect(id);
            setAccounts((prev) => prev.filter((a) => a.id !== id));
        } catch (err) {
            setConnectError(err instanceof Error ? err.message : "Error al desconectar la cuenta");
        }
    };

    return (
        <div className="space-y-4">
        {connectError && (
            <div className="flex items-center gap-2 text-red-400 text-xs bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
                <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                {connectError}
            </div>
        )}
        {config && !config.proxy && Object.values(config.platforms).every((v) => !v) && (
            <div className="flex items-start gap-2 text-amber-400 text-xs bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-2">
                <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                <span>
                    No hay credenciales de redes configuradas. Define las apps de desarrollador
                    (o un proxy OAuth) en el backend. Guía: <code>docs/oauth-social-setup.md</code>.
                </span>
            </div>
        )}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {CONNECTABLE_PLATFORMS.map((p) => {
                const Icon = PLATFORM_ICONS[p.id];
                const account = accounts.find((a) => a.platform === p.id && a.is_active);
                const isConnecting = connecting === p.id;
                const expiry = account ? tokenStatus(account.token_expires_at) : null;
                const notConfigured = config ? config.platforms[p.id] === false : false;

                return (
                    <div key={p.id} className="bg-card border border-border rounded-xl p-4 flex items-start gap-4">
                        <div className={`p-2.5 rounded-xl ${p.iconBg} flex-shrink-0`}>
                            <Icon className={`w-5 h-5 ${p.colorClass.split(" ")[0]}`} />
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-foreground">{p.name}</p>
                            {account ? (
                                <>
                                    <p className="text-xs text-muted-foreground truncate mt-0.5">
                                        {account.account_name ?? account.account_id}
                                    </p>
                                    <div className="flex items-center gap-1.5 mt-2">
                                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                                        <span className="text-[11px] text-emerald-400">Conectado</span>
                                        <button
                                            onClick={() => disconnect(account.id)}
                                            className="ml-auto text-[11px] text-muted-foreground hover:text-red-400 transition-colors"
                                        >
                                            Desconectar
                                        </button>
                                    </div>
                                    {expiry && (
                                        <button
                                            onClick={() => connect(p.id)}
                                            disabled={isConnecting}
                                            title="Vuelve a autorizar para renovar el token"
                                            className={`flex items-center gap-1.5 mt-2 text-[11px] ${expiry.level === "expired" ? "text-red-400" : "text-amber-400"} hover:underline disabled:opacity-50`}
                                        >
                                            <AlertTriangle className="w-3 h-3 flex-shrink-0" />
                                            {expiry.label}
                                        </button>
                                    )}
                                </>
                            ) : notConfigured ? (
                                <>
                                    <p className="text-xs text-muted-foreground mt-0.5">No conectado</p>
                                    <div className="flex items-center gap-1.5 mt-2 text-[11px] text-amber-400" title="Faltan las credenciales de esta plataforma en el backend">
                                        <AlertTriangle className="w-3 h-3 flex-shrink-0" />
                                        Falta configurar credenciales
                                    </div>
                                </>
                            ) : (
                                <>
                                    <p className="text-xs text-muted-foreground mt-0.5">No conectado</p>
                                    <button
                                        onClick={() => connect(p.id)}
                                        disabled={isConnecting}
                                        className={`mt-2 flex items-center gap-1.5 text-[11px] px-3 py-1.5 rounded-lg border transition-colors ${p.colorClass} hover:opacity-80 disabled:opacity-50`}
                                    >
                                        {isConnecting
                                            ? <Loader2 className="w-3 h-3 animate-spin" />
                                            : <Plus className="w-3 h-3" />}
                                        Conectar
                                    </button>
                                </>
                            )}
                        </div>
                    </div>
                );
            })}
        </div>
        </div>
    );
}
