"use client";

import { useEffect, useState, useCallback } from "react";
import { CheckCircle2, XCircle, Loader2, Plug, PlugZap, Building2, Mail, Cloud, HardDrive } from "lucide-react";
import { api, IntegrationStatus } from "@/lib/api";
import { showConfirm } from "@/stores/confirm";
import { logError } from "@/lib/logger";

/* ─── OAuth popup helper ─────────────────────────────────────────────────── */

function openOAuthPopup(url: string, onSuccess: () => void) {
    const w = 500, h = 600;
    const left = window.screenX + (window.outerWidth - w) / 2;
    const top = window.screenY + (window.outerHeight - h) / 2;
    const popup = window.open(url, "oauth_popup", `width=${w},height=${h},left=${left},top=${top}`);

    const handler = (event: MessageEvent) => {
        if (event.data?.type === "oauth_success") {
            window.removeEventListener("message", handler);
            onSuccess();
        }
    };
    window.addEventListener("message", handler);

    // Fallback: poll for popup close
    const interval = setInterval(() => {
        if (popup?.closed) {
            clearInterval(interval);
            window.removeEventListener("message", handler);
            onSuccess();
        }
    }, 500);
}

/* ─── Status badge ───────────────────────────────────────────────────────── */

function StatusBadge({ loading, connected }: { loading: boolean; connected: boolean }) {
    if (loading) return <Loader2 className="w-4 h-4 text-zinc-500 animate-spin" />;
    if (connected) return <div className="flex items-center gap-2 text-emerald-400 text-sm"><CheckCircle2 className="w-4 h-4" /> Conectado</div>;
    return <div className="flex items-center gap-2 text-zinc-500 text-sm"><XCircle className="w-4 h-4" /> No conectado</div>;
}

/* ─── Card wrapper ───────────────────────────────────────────────────────── */

function IntegrationCard({
    icon, iconBg, title, subtitle, loading, connected, lastSync, children,
}: {
    icon: React.ReactNode; iconBg: string; title: string; subtitle: string;
    loading: boolean; connected: boolean; lastSync?: string; children: React.ReactNode;
}) {
    return (
        <div className="rounded-xl border border-[#27272a] bg-[#111113] overflow-hidden">
            <div className="flex items-center justify-between px-6 py-5 border-b border-[#27272a]">
                <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-lg ${iconBg} flex items-center justify-center`}>{icon}</div>
                    <div>
                        <p className="font-semibold text-white">{title}</p>
                        <p className="text-xs text-zinc-500">{subtitle}</p>
                    </div>
                </div>
                <StatusBadge loading={loading} connected={connected} />
            </div>
            <div className="px-6 py-5">
                {connected && lastSync && (
                    <p className="text-xs text-zinc-500 mb-3">
                        Última sincronización: {new Date(lastSync).toLocaleString("es-ES")}
                    </p>
                )}
                {children}
            </div>
        </div>
    );
}

/* ─── Main Page ──────────────────────────────────────────────────────────── */

export default function IntegracionesPage() {
    const [integrations, setIntegrations] = useState<IntegrationStatus[]>([]);
    const [loading, setLoading] = useState(true);
    const [feedback, setFeedback] = useState<{ type: "success" | "error"; msg: string } | null>(null);

    // Holded
    const [holdedKey, setHoldedKey] = useState("");
    const [connectingHolded, setConnectingHolded] = useState(false);
    const [disconnectingHolded, setDisconnectingHolded] = useState(false);

    // PSD2
    const [psd2Id, setPsd2Id] = useState("");
    const [psd2Key, setPsd2Key] = useState("");
    const [connectingPsd2, setConnectingPsd2] = useState(false);
    const [disconnectingPsd2, setDisconnectingPsd2] = useState(false);

    // OAuth loading states
    const [connectingGoogle, setConnectingGoogle] = useState(false);
    const [connectingMicrosoft, setConnectingMicrosoft] = useState(false);

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const data = await api.integrations.list();
            setIntegrations(data);
        } catch (err) {
            logError("integraciones/page", err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { load(); }, [load]);

    // Check URL params for OAuth redirect fallback
    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        const connected = params.get("connected");
        if (connected) {
            setFeedback({ type: "success", msg: `${connected === "google" ? "Google" : "Microsoft"} conectado correctamente` });
            window.history.replaceState({}, "", "/integraciones");
            load();
        }
    }, [load]);

    // Statuses
    const getStatus = (type: string) => integrations.find(i => i.integration_type === type);
    const isConnected = (type: string) => getStatus(type)?.is_active ?? false;

    // ─── Holded Handlers ─────────────────────────────────────────────────────

    async function connectHolded(e: React.FormEvent) {
        e.preventDefault();
        setConnectingHolded(true); setFeedback(null);
        try {
            await api.integrations.connectHolded(holdedKey);
            setFeedback({ type: "success", msg: "Holded conectado correctamente" });
            setHoldedKey("");
            load();
        } catch (err: unknown) {
            setFeedback({ type: "error", msg: err instanceof Error ? err.message : "Error desconocido" });
        } finally {
            setConnectingHolded(false);
        }
    }

    async function disconnectHolded() {
        if (!await showConfirm({ message: "¿Desconectar Holded?", confirmLabel: "Desconectar", confirmVariant: "danger" })) return;
        setDisconnectingHolded(true); setFeedback(null);
        try {
            await api.integrations.disconnectHolded();
            setFeedback({ type: "success", msg: "Holded desconectado" });
            load();
        } catch (err: unknown) {
            setFeedback({ type: "error", msg: err instanceof Error ? err.message : "Error" });
        } finally {
            setDisconnectingHolded(false);
        }
    }

    // ─── PSD2 Handlers ───────────────────────────────────────────────────────

    async function connectPsd2(e: React.FormEvent) {
        e.preventDefault();
        setConnectingPsd2(true); setFeedback(null);
        try {
            await api.integrations.connectPsd2(psd2Id, psd2Key);
            setFeedback({ type: "success", msg: "Banco (PSD2) conectado correctamente" });
            setPsd2Id(""); setPsd2Key("");
            load();
        } catch (err: unknown) {
            setFeedback({ type: "error", msg: err instanceof Error ? err.message : "Error desconocido" });
        } finally {
            setConnectingPsd2(false);
        }
    }

    async function disconnectPsd2() {
        if (!await showConfirm({ message: "¿Desconectar tu Banco?", confirmLabel: "Desconectar", confirmVariant: "danger" })) return;
        setDisconnectingPsd2(true); setFeedback(null);
        try {
            await api.integrations.disconnectPsd2();
            setFeedback({ type: "success", msg: "Banco desconectado" });
            load();
        } catch (err: unknown) {
            setFeedback({ type: "error", msg: err instanceof Error ? err.message : "Error" });
        } finally {
            setDisconnectingPsd2(false);
        }
    }

    // ─── OAuth Handlers ──────────────────────────────────────────────────────

    async function connectOAuth(provider: "google" | "microsoft") {
        const setConnecting = provider === "google" ? setConnectingGoogle : setConnectingMicrosoft;
        setConnecting(true); setFeedback(null);
        try {
            const data = await api.integrations.oauthUrl(provider);
            openOAuthPopup(data.auth_url, () => {
                setConnecting(false);
                setFeedback({ type: "success", msg: `${provider === "google" ? "Google" : "Microsoft"} conectado` });
                load();
            });
        } catch (err: unknown) {
            setConnecting(false);
            setFeedback({ type: "error", msg: err instanceof Error ? err.message : "Error" });
        }
    }

    async function disconnectIntegration(type: string, label: string) {
        if (!await showConfirm({ message: `¿Desconectar ${label}?`, confirmLabel: "Desconectar", confirmVariant: "danger" })) return;
        setFeedback(null);
        try {
            await api.integrations.disconnect(type);
            setFeedback({ type: "success", msg: `${label} desconectado` });
            load();
        } catch (err: unknown) {
            setFeedback({ type: "error", msg: err instanceof Error ? err.message : "Error" });
        }
    }

    // ─── UI ──────────────────────────────────────────────────────────────────

    return (
        <div className="p-8 max-w-3xl mx-auto space-y-8">
            <div>
                <h1 className="text-2xl font-bold text-white">Integraciones</h1>
                <p className="text-sm text-zinc-400 mt-1">
                    Conecta tus herramientas para que los agentes puedan actuar sobre ellas
                </p>
            </div>

            {feedback && (
                <div className={`px-4 py-3 rounded-lg border text-sm ${feedback.type === "success"
                    ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                    : "bg-red-500/10 border-red-500/20 text-red-400"
                }`}>
                    {feedback.msg}
                </div>
            )}

            {/* ── Holded ────────────────────────────────────────────────────── */}
            <IntegrationCard
                icon={<PlugZap className="w-5 h-5 text-blue-400" />}
                iconBg="bg-[#1a1aff]/20"
                title="Holded" subtitle="ERP y facturación"
                loading={loading} connected={isConnected("holded")}
                lastSync={getStatus("holded")?.last_sync_at}
            >
                {isConnected("holded") ? (
                    <div className="space-y-4">
                        <p className="text-sm text-zinc-400">El agente de facturación puede crear y enviar facturas a través de tu cuenta de Holded.</p>
                        <button onClick={disconnectHolded} disabled={disconnectingHolded}
                            className="px-4 py-2 rounded-lg border border-red-500/30 text-red-400 hover:bg-red-500/10 disabled:opacity-50 text-sm transition">
                            {disconnectingHolded ? "Desconectando…" : "Desconectar Holded"}
                        </button>
                    </div>
                ) : (
                    <form onSubmit={connectHolded} className="space-y-4">
                        <p className="text-sm text-zinc-400 mb-3">Introduce tu API key de Holded (ajustes → API).</p>
                        <input type="password" required value={holdedKey} onChange={e => setHoldedKey(e.target.value)}
                            placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                            className="w-full px-4 py-2.5 rounded-lg bg-[#18181b] border border-[#3f3f46] text-white text-sm placeholder-zinc-600 font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500 transition" />
                        <button type="submit" disabled={connectingHolded || !holdedKey.trim()}
                            className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium transition">
                            {connectingHolded ? <><Loader2 className="w-4 h-4 animate-spin" /> Verificando…</> : <><Plug className="w-4 h-4" /> Conectar Holded</>}
                        </button>
                    </form>
                )}
            </IntegrationCard>

            {/* ── Banco PSD2 ─────────────────────────────────────────────────── */}
            <IntegrationCard
                icon={<Building2 className="w-5 h-5 text-emerald-400" />}
                iconBg="bg-emerald-500/10 border border-emerald-500/20"
                title="Banco (PSD2 / GoCardless)" subtitle="Saldos y transacciones reales"
                loading={loading} connected={isConnected("psd2")}
                lastSync={getStatus("psd2")?.last_sync_at}
            >
                {isConnected("psd2") ? (
                    <div className="space-y-4">
                        <p className="text-sm text-emerald-400/90 bg-emerald-500/10 px-4 py-3 border border-emerald-500/20 rounded-lg">
                            Tu agente de finanzas ahora puede consultar tus saldos y transacciones bancarias en tiempo real.
                        </p>
                        <button onClick={disconnectPsd2} disabled={disconnectingPsd2}
                            className="px-4 py-2 rounded-lg border border-red-500/30 text-red-400 hover:bg-red-500/10 disabled:opacity-50 text-sm transition">
                            {disconnectingPsd2 ? "Desconectando…" : "Desconectar Banco"}
                        </button>
                    </div>
                ) : (
                    <form onSubmit={connectPsd2} className="space-y-4">
                        <p className="text-sm text-zinc-400 mb-4 leading-relaxed">
                            Para conectarte a tus cuentas bancarias usamos GoCardless (antes Nordigen), un agregador regulado bajo directiva <strong className="text-zinc-300">PSD2</strong> europea.
                        </p>
                        <div className="space-y-3">
                            <input type="text" required value={psd2Id} onChange={e => setPsd2Id(e.target.value)}
                                placeholder="Secret ID (puedes usar: DEMO_PSD2_ID)"
                                className="w-full px-4 py-2.5 rounded-lg bg-[#18181b] border border-[#3f3f46] text-white text-sm placeholder-zinc-600 font-mono focus:outline-none focus:ring-2 focus:ring-emerald-500 transition" />
                            <input type="password" required value={psd2Key} onChange={e => setPsd2Key(e.target.value)}
                                placeholder="Secret Key (puedes usar: DEMO_PSD2_ID)"
                                className="w-full px-4 py-2.5 rounded-lg bg-[#18181b] border border-[#3f3f46] text-white text-sm placeholder-zinc-600 font-mono focus:outline-none focus:ring-2 focus:ring-emerald-500 transition" />
                        </div>
                        <button type="submit" disabled={connectingPsd2 || !psd2Id.trim() || !psd2Key.trim()}
                            className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-sm font-medium transition">
                            {connectingPsd2 ? <><Loader2 className="w-4 h-4 animate-spin" /> Verificando…</> : <><Plug className="w-4 h-4" /> Conectar PSD2</>}
                        </button>
                    </form>
                )}
            </IntegrationCard>

            {/* ── Gmail ──────────────────────────────────────────────────────── */}
            <IntegrationCard
                icon={<Mail className="w-5 h-5 text-red-400" />}
                iconBg="bg-red-500/10 border border-red-500/20"
                title="Gmail" subtitle="Correo electrónico con Google"
                loading={loading} connected={isConnected("gmail")}
                lastSync={getStatus("gmail")?.last_sync_at}
            >
                {isConnected("gmail") ? (
                    <div className="space-y-4">
                        <p className="text-sm text-zinc-400">El agente de email puede leer y enviar correos desde tu cuenta de Gmail.</p>
                        <button onClick={() => disconnectIntegration("gmail", "Gmail")}
                            className="px-4 py-2 rounded-lg border border-red-500/30 text-red-400 hover:bg-red-500/10 text-sm transition">
                            Desconectar Gmail
                        </button>
                    </div>
                ) : (
                    <div className="space-y-4">
                        <p className="text-sm text-zinc-400">Conecta tu cuenta de Gmail para que el agente pueda leer tu bandeja de entrada y enviar correos en tu nombre.</p>
                        <button onClick={() => connectOAuth("google")} disabled={connectingGoogle}
                            className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white text-sm font-medium transition">
                            {connectingGoogle ? <><Loader2 className="w-4 h-4 animate-spin" /> Conectando…</> : <><Mail className="w-4 h-4" /> Conectar con Google</>}
                        </button>
                        <p className="text-xs text-zinc-600">Al conectar Google se habilitan Gmail y Google Drive simultáneamente.</p>
                    </div>
                )}
            </IntegrationCard>

            {/* ── Google Drive ───────────────────────────────────────────────── */}
            <IntegrationCard
                icon={<HardDrive className="w-5 h-5 text-yellow-400" />}
                iconBg="bg-yellow-500/10 border border-yellow-500/20"
                title="Google Drive" subtitle="Almacenamiento y backup de documentos"
                loading={loading} connected={isConnected("gdrive")}
                lastSync={getStatus("gdrive")?.last_sync_at}
            >
                {isConnected("gdrive") ? (
                    <div className="space-y-4">
                        <p className="text-sm text-zinc-400">
                            Sincroniza documentos, sube facturas y realiza backups automáticos en tu Google Drive.
                        </p>
                        <button onClick={() => disconnectIntegration("gdrive", "Google Drive")}
                            className="px-4 py-2 rounded-lg border border-red-500/30 text-red-400 hover:bg-red-500/10 text-sm transition">
                            Desconectar Google Drive
                        </button>
                    </div>
                ) : (
                    <div className="space-y-4">
                        <p className="text-sm text-zinc-400">Conecta Google Drive para sincronizar documentos, exportar facturas y hacer backups automáticos.</p>
                        {isConnected("gmail") ? (
                            <p className="text-sm text-emerald-400/90 bg-emerald-500/10 px-4 py-3 border border-emerald-500/20 rounded-lg">
                                Google Drive ya está conectado junto con Gmail. Actívalo arriba.
                            </p>
                        ) : (
                            <button onClick={() => connectOAuth("google")} disabled={connectingGoogle}
                                className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-yellow-600 hover:bg-yellow-500 disabled:opacity-50 text-white text-sm font-medium transition">
                                {connectingGoogle ? <><Loader2 className="w-4 h-4 animate-spin" /> Conectando…</> : <><HardDrive className="w-4 h-4" /> Conectar con Google</>}
                            </button>
                        )}
                    </div>
                )}
            </IntegrationCard>

            {/* ── Outlook ────────────────────────────────────────────────────── */}
            <IntegrationCard
                icon={<Mail className="w-5 h-5 text-blue-400" />}
                iconBg="bg-blue-500/10 border border-blue-500/20"
                title="Outlook" subtitle="Correo electrónico con Microsoft"
                loading={loading} connected={isConnected("outlook")}
                lastSync={getStatus("outlook")?.last_sync_at}
            >
                {isConnected("outlook") ? (
                    <div className="space-y-4">
                        <p className="text-sm text-zinc-400">El agente de email puede leer y enviar correos desde tu cuenta de Outlook.</p>
                        <button onClick={() => disconnectIntegration("outlook", "Outlook")}
                            className="px-4 py-2 rounded-lg border border-red-500/30 text-red-400 hover:bg-red-500/10 text-sm transition">
                            Desconectar Outlook
                        </button>
                    </div>
                ) : (
                    <div className="space-y-4">
                        <p className="text-sm text-zinc-400">Conecta tu cuenta de Outlook / Microsoft 365 para que el agente gestione tu correo.</p>
                        <button onClick={() => connectOAuth("microsoft")} disabled={connectingMicrosoft}
                            className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm font-medium transition">
                            {connectingMicrosoft ? <><Loader2 className="w-4 h-4 animate-spin" /> Conectando…</> : <><Mail className="w-4 h-4" /> Conectar con Microsoft</>}
                        </button>
                        <p className="text-xs text-zinc-600">Al conectar Microsoft se habilitan Outlook y OneDrive simultáneamente.</p>
                    </div>
                )}
            </IntegrationCard>

            {/* ── Microsoft 365 / OneDrive ───────────────────────────────────── */}
            <IntegrationCard
                icon={<Cloud className="w-5 h-5 text-sky-400" />}
                iconBg="bg-sky-500/10 border border-sky-500/20"
                title="Microsoft 365 / OneDrive" subtitle="Almacenamiento y backup de documentos"
                loading={loading} connected={isConnected("onedrive")}
                lastSync={getStatus("onedrive")?.last_sync_at}
            >
                {isConnected("onedrive") ? (
                    <div className="space-y-4">
                        <p className="text-sm text-zinc-400">
                            Sincroniza documentos, sube facturas y realiza backups automáticos en tu OneDrive.
                        </p>
                        <button onClick={() => disconnectIntegration("onedrive", "OneDrive")}
                            className="px-4 py-2 rounded-lg border border-red-500/30 text-red-400 hover:bg-red-500/10 text-sm transition">
                            Desconectar OneDrive
                        </button>
                    </div>
                ) : (
                    <div className="space-y-4">
                        <p className="text-sm text-zinc-400">Conecta OneDrive para sincronizar documentos, exportar facturas y hacer backups automáticos.</p>
                        {isConnected("outlook") ? (
                            <p className="text-sm text-emerald-400/90 bg-emerald-500/10 px-4 py-3 border border-emerald-500/20 rounded-lg">
                                OneDrive ya está conectado junto con Outlook. Actívalo arriba.
                            </p>
                        ) : (
                            <button onClick={() => connectOAuth("microsoft")} disabled={connectingMicrosoft}
                                className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white text-sm font-medium transition">
                                {connectingMicrosoft ? <><Loader2 className="w-4 h-4 animate-spin" /> Conectando…</> : <><Cloud className="w-4 h-4" /> Conectar con Microsoft</>}
                            </button>
                        )}
                    </div>
                )}
            </IntegrationCard>
        </div>
    );
}
