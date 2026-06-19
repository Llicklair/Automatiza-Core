"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslations } from "next-intl";
import { Loader2, CheckCircle2, AlertCircle, Plus, Trash2, KeyRound, Share2 } from "lucide-react";
import { marketingApi, SocialAccount, ZernioConfig } from "@/lib/api/marketing";
import { PLATFORM_ICONS } from "@/components/ui/social-icons";
import { CONNECTABLE_PLATFORMS } from "./constants";

// ── Tab: Cuentas (BYO Zernio) ────────────────────────────────────────────────
// Las redes se conectan a través de Zernio. Cada cuenta de Zernio (un email/API
// key) da 2 redes gratis; el usuario puede añadir varias para conectar más.

// Abre un enlace en el navegador del sistema (Electron) o en una pestaña nueva.
function openExternal(url: string) {
    const eAPI = (window as typeof window & {
        electronAPI?: { openExternal?: (u: string) => Promise<void> };
    }).electronAPI;
    if (eAPI?.openExternal) eAPI.openExternal(url);
    else window.open(url, "_blank");
}

export function TabCuentas() {
    const t = useTranslations("marketing.cuentas");
    const tc = useTranslations("marketing.common");
    const [configs, setConfigs] = useState<ZernioConfig[]>([]);
    const [accounts, setAccounts] = useState<SocialAccount[]>([]);
    const [selectedConfigId, setSelectedConfigId] = useState<string>("");
    const [loading, setLoading] = useState(true);
    const [connecting, setConnecting] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);

    // Form para añadir una cuenta de Zernio
    const [showAdd, setShowAdd] = useState(false);
    const [newKey, setNewKey] = useState("");
    const [newLabel, setNewLabel] = useState("");
    const [adding, setAdding] = useState(false);

    const load = useCallback(async () => {
        try {
            const [cfgs, accs] = await Promise.all([
                marketingApi.zernioConfig.list(),
                marketingApi.accounts.list().catch(() => [] as SocialAccount[]),
            ]);
            setConfigs(cfgs);
            setAccounts(accs);
            setSelectedConfigId((prev) => prev || (cfgs[0]?.id ?? ""));
        } catch {
            // sin configurar aún
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { load(); }, [load]);

    // Refresca cuando el popup de conexión cierra con éxito (postMessage)
    useEffect(() => {
        const handler = (e: MessageEvent) => {
            if (e.data?.type === "oauth-complete") load();
        };
        window.addEventListener("message", handler);
        return () => window.removeEventListener("message", handler);
    }, [load]);

    const addConfig = async () => {
        const key = newKey.trim();
        if (!key.startsWith("sk_")) {
            setError(t("addConfigError"));
            return;
        }
        setAdding(true);
        setError(null);
        try {
            const cfg = await marketingApi.zernioConfig.add({
                api_key: key,
                label: newLabel.trim() || undefined,
            });
            setConfigs((prev) => [...prev, cfg]);
            setSelectedConfigId((prev) => prev || cfg.id);
            setNewKey(""); setNewLabel(""); setShowAdd(false);
        } catch (err) {
            setError(err instanceof Error ? err.message : t("addConfigFail"));
        } finally {
            setAdding(false);
        }
    };

    const deleteConfig = async (id: string) => {
        try {
            await marketingApi.zernioConfig.delete(id);
            setConfigs((prev) => prev.filter((c) => c.id !== id));
            setSelectedConfigId((prev) => (prev === id ? "" : prev));
            load();
        } catch (err) {
            setError(err instanceof Error ? err.message : t("deleteConfigFail"));
        }
    };

    const connect = async (platform: string) => {
        if (!selectedConfigId) {
            setError(t("selectConfigFirst"));
            return;
        }
        setConnecting(platform);
        setError(null);
        try {
            const { auth_url } = await marketingApi.accounts.connect(platform, selectedConfigId);
            // En Electron, los OAuth de redes abren en el navegador del sistema.
            const eAPI = (window as typeof window & {
                electronAPI?: { openExternal?: (u: string) => Promise<void> };
            }).electronAPI;
            if (eAPI?.openExternal) {
                await eAPI.openExternal(auth_url);
            } else {
                window.open(auth_url, "_blank", "width=600,height=700");
            }
            // Polling hasta 60s para detectar la nueva cuenta cuando llegue el callback
            const before = accounts.map((a) => a.id);
            let attempts = 0;
            const iv = setInterval(async () => {
                attempts++;
                try {
                    const fresh = await marketingApi.accounts.list();
                    if (fresh.some((a) => !before.includes(a.id))) {
                        setAccounts(fresh);
                        load();
                        clearInterval(iv);
                    }
                } catch { /* ignore */ }
                if (attempts >= 30) clearInterval(iv);
            }, 2000);
        } catch (err) {
            setError(err instanceof Error ? err.message : t("connectError"));
        } finally {
            setConnecting(null);
        }
    };

    const disconnect = async (id: string) => {
        try {
            await marketingApi.accounts.disconnect(id);
            setAccounts((prev) => prev.filter((a) => a.id !== id));
            load();
        } catch (err) {
            setError(err instanceof Error ? err.message : t("disconnectError"));
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-10 text-muted-foreground">
                <Loader2 className="w-4 h-4 animate-spin mr-2" /> {tc("loading")}
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {error && (
                <div className="flex items-center gap-2 text-red-400 text-xs bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
                    <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                    {error}
                </div>
            )}

            {/* ── Cuentas de Zernio ── */}
            <div className="space-y-3">
                <div className="flex items-center justify-between">
                    <h3 className="text-sm font-medium text-foreground flex items-center gap-2">
                        <KeyRound className="w-4 h-4 text-muted-foreground" /> {t("zernioAccounts")}
                    </h3>
                    {configs.length > 0 && (
                        <button
                            onClick={() => setShowAdd((v) => !v)}
                            className="text-[11px] text-muted-foreground hover:text-foreground flex items-center gap-1"
                        >
                            <Plus className="w-3 h-3" /> {t("addAnother")}
                        </button>
                    )}
                </div>
                <p className="text-[11px] text-muted-foreground">
                    {t("introBefore")}{" "}
                    <strong>{t("introStrong")}</strong>{t("introAfter")}{" "}
                    <button
                        type="button"
                        onClick={() => openExternal("https://zernio.com/signup")}
                        className="text-indigo-400 hover:underline"
                    >
                        {t("createFreeAccount")}
                    </button>
                </p>

                {configs.map((c) => (
                    <div key={c.id} className="bg-card border border-border rounded-xl p-3 flex items-center gap-3">
                        <div className="flex-1 min-w-0">
                            <p className="text-sm text-foreground truncate">{c.label || t("defaultConfigLabel")}</p>
                            <p className="text-[11px] text-muted-foreground">{t("networksUsed", { used: c.num_accounts })}</p>
                        </div>
                        <button
                            onClick={() => deleteConfig(c.id)}
                            className="text-muted-foreground hover:text-red-400 transition-colors"
                            title={t("deleteConfigTitle")}
                        >
                            <Trash2 className="w-3.5 h-3.5" />
                        </button>
                    </div>
                ))}

                {(showAdd || configs.length === 0) && (
                    <div className="bg-card border border-border rounded-xl p-3 space-y-2">
                        <input
                            value={newLabel}
                            onChange={(e) => setNewLabel(e.target.value)}
                            placeholder={t("labelPlaceholder")}
                            className="w-full bg-background border border-border rounded-lg px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground"
                        />
                        <input
                            value={newKey}
                            onChange={(e) => setNewKey(e.target.value)}
                            placeholder={t("apiKeyPlaceholder")}
                            type="password"
                            className="w-full bg-background border border-border rounded-lg px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground font-mono"
                        />
                        <div className="flex items-center gap-2">
                            <button
                                onClick={addConfig}
                                disabled={adding}
                                className="flex items-center gap-1.5 text-[11px] px-3 py-1.5 rounded-lg border border-indigo-500/40 text-indigo-300 hover:bg-indigo-500/10 disabled:opacity-50"
                            >
                                {adding ? <Loader2 className="w-3 h-3 animate-spin" /> : <Plus className="w-3 h-3" />}
                                {t("addAndValidate")}
                            </button>
                            {configs.length > 0 && (
                                <button
                                    onClick={() => { setShowAdd(false); setNewKey(""); setNewLabel(""); }}
                                    className="text-[11px] text-muted-foreground hover:text-foreground"
                                >
                                    {tc("cancel")}
                                </button>
                            )}
                        </div>
                        <p className="text-[10px] text-muted-foreground">
                            {t("keyEncryptedNote")}{" "}
                            <button
                                type="button"
                                onClick={() => openExternal("https://zernio.com/dashboard/api-keys")}
                                className="text-indigo-400 hover:underline"
                            >
                                {t("getApiKey")}
                            </button>
                        </p>
                    </div>
                )}
            </div>

            {/* ── Conectar redes ── */}
            {configs.length > 0 && (
                <div className="space-y-3">
                    <div className="flex items-center justify-between gap-2">
                        <h3 className="text-sm font-medium text-foreground">{t("connectNetworks")}</h3>
                        {configs.length > 1 && (
                            <select
                                value={selectedConfigId}
                                onChange={(e) => setSelectedConfigId(e.target.value)}
                                className="bg-background border border-border rounded-lg px-2 py-1 text-[11px] text-foreground"
                            >
                                {configs.map((c) => (
                                    <option key={c.id} value={c.id}>
                                        {t("configOption", { label: c.label || t("defaultConfigLabel"), used: c.num_accounts })}
                                    </option>
                                ))}
                            </select>
                        )}
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        {CONNECTABLE_PLATFORMS.map((p) => {
                            const Icon = PLATFORM_ICONS[p.id] ?? Share2;
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
                                                    <span className="text-[11px] text-emerald-400">{t("connected")}</span>
                                                    <button
                                                        onClick={() => disconnect(account.id)}
                                                        className="ml-auto text-[11px] text-muted-foreground hover:text-red-400 transition-colors"
                                                    >
                                                        {t("disconnect")}
                                                    </button>
                                                </div>
                                            </>
                                        ) : (
                                            <>
                                                <p className="text-xs text-muted-foreground mt-0.5">{t("notConnected")}</p>
                                                <button
                                                    onClick={() => connect(p.id)}
                                                    disabled={isConnecting}
                                                    className={`mt-2 flex items-center gap-1.5 text-[11px] px-3 py-1.5 rounded-lg border transition-colors ${p.colorClass} hover:opacity-80 disabled:opacity-50`}
                                                >
                                                    {isConnecting
                                                        ? <Loader2 className="w-3 h-3 animate-spin" />
                                                        : <Plus className="w-3 h-3" />}
                                                    {t("connect")}
                                                </button>
                                            </>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}
        </div>
    );
}
