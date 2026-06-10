"use client";

import { useState, useEffect, useCallback } from "react";
import { Loader2, CheckCircle2, AlertCircle, Plus } from "lucide-react";
import { marketingApi, SocialAccount } from "@/lib/api/marketing";
import { PLATFORM_ICONS } from "@/components/ui/social-icons";
import { PLATFORMS } from "./constants";

// ── Tab: Cuentas ───────────────────────────────────────────────────────────────

export function TabCuentas() {
    const [accounts, setAccounts] = useState<SocialAccount[]>([]);
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
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {PLATFORMS.map((p) => {
                const Icon = PLATFORM_ICONS[p.id];
                const account = accounts.find((a) => a.platform === p.id && a.is_active);
                const isConnecting = connecting === p.id;

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
