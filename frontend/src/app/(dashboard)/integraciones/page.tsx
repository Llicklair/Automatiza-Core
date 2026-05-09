"use client";

import { useState } from "react";
import { CheckCircle2, XCircle, Loader2, Plug, Building2, Mail, Cloud, HardDrive, Server } from "lucide-react";
import InfoBanner from "@/components/InfoBanner";
import { useIntegraciones } from "./_hooks/useIntegraciones";

const SMTP_PRESETS: Record<string, { imap_host: string; imap_port: number; smtp_host: string; smtp_port: number; help: string }> = {
    gmail: { imap_host: "imap.gmail.com", imap_port: 993, smtp_host: "smtp.gmail.com", smtp_port: 587, help: "Necesitas una App Password (no tu contraseña normal). Genérala en myaccount.google.com → Seguridad → Verificación en dos pasos → Contraseñas de aplicaciones." },
    outlook: { imap_host: "outlook.office365.com", imap_port: 993, smtp_host: "smtp.office365.com", smtp_port: 587, help: "Usa tu contraseña habitual o una contraseña de aplicación si tienes 2FA." },
    yahoo: { imap_host: "imap.mail.yahoo.com", imap_port: 993, smtp_host: "smtp.mail.yahoo.com", smtp_port: 587, help: "Yahoo exige App Password. Ve a Configuración → Seguridad de la cuenta → Generar contraseña de aplicación." },
    icloud: { imap_host: "imap.mail.me.com", imap_port: 993, smtp_host: "smtp.mail.me.com", smtp_port: 587, help: "Necesitas una App Password de Apple. Genérala en appleid.apple.com → Inicio de sesión y seguridad → Contraseñas específicas para apps." },
    custom: { imap_host: "", imap_port: 993, smtp_host: "", smtp_port: 587, help: "Introduce los datos de tu proveedor. Pregunta a tu administrador si no los conoces." },
};

function StatusBadge({ loading, connected }: { loading: boolean; connected: boolean }) {
    if (loading) return <Loader2 className="w-4 h-4 text-muted-foreground animate-spin" />;
    if (connected) return <div className="flex items-center gap-2 text-emerald-400 text-sm"><CheckCircle2 className="w-4 h-4" /> Conectado</div>;
    return <div className="flex items-center gap-2 text-muted-foreground text-sm"><XCircle className="w-4 h-4" /> No conectado</div>;
}

function IntegrationCard({
    icon, iconBg, title, subtitle, loading, connected, lastSync, children,
}: {
    icon: React.ReactNode; iconBg: string; title: string; subtitle: string;
    loading: boolean; connected: boolean; lastSync?: string; children: React.ReactNode;
}) {
    return (
        <div className="rounded-xl border border-border bg-card overflow-hidden">
            <div className="flex items-center justify-between px-6 py-5 border-b border-border">
                <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-lg ${iconBg} flex items-center justify-center`}>{icon}</div>
                    <div>
                        <p className="font-semibold text-foreground">{title}</p>
                        <p className="text-xs text-muted-foreground">{subtitle}</p>
                    </div>
                </div>
                <StatusBadge loading={loading} connected={connected} />
            </div>
            <div className="px-6 py-5">
                {connected && lastSync && (
                    <p className="text-xs text-muted-foreground mb-3">
                        Última sincronización: {new Date(lastSync).toLocaleString("es-ES")}
                    </p>
                )}
                {children}
            </div>
        </div>
    );
}

function EmailSmtpForm({
    onSubmit, busy,
}: {
    onSubmit: (payload: { email_address: string; password: string; provider: string; imap_host?: string; imap_port?: number; smtp_host?: string; smtp_port?: number }) => Promise<boolean>;
    busy: boolean;
}) {
    const [provider, setProvider] = useState("gmail");
    const [emailAddr, setEmailAddr] = useState("");
    const [password, setPassword] = useState("");
    const preset = SMTP_PRESETS[provider] ?? SMTP_PRESETS.custom;
    const [imapHost, setImapHost] = useState(preset.imap_host);
    const [imapPort, setImapPort] = useState(preset.imap_port);
    const [smtpHost, setSmtpHost] = useState(preset.smtp_host);
    const [smtpPort, setSmtpPort] = useState(preset.smtp_port);

    function handleProviderChange(next: string) {
        setProvider(next);
        const p = SMTP_PRESETS[next] ?? SMTP_PRESETS.custom;
        setImapHost(p.imap_host);
        setImapPort(p.imap_port);
        setSmtpHost(p.smtp_host);
        setSmtpPort(p.smtp_port);
    }

    async function submit(e: React.FormEvent) {
        e.preventDefault();
        const ok = await onSubmit({
            email_address: emailAddr.trim(),
            password,
            provider,
            imap_host: imapHost || undefined,
            imap_port: imapPort || undefined,
            smtp_host: smtpHost || undefined,
            smtp_port: smtpPort || undefined,
        });
        if (ok) { setPassword(""); }
    }

    return (
        <form onSubmit={submit} className="space-y-4">
            <p className="text-sm text-muted-foreground leading-relaxed">
                Conexión vía IMAP/SMTP — útil para servidores propios, Yahoo, iCloud o cuando OAuth no esté disponible.
                Para <strong className="text-foreground">Gmail</strong> y <strong className="text-foreground">Outlook</strong> recomendamos OAuth (botones arriba).
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <label className="space-y-1.5 text-sm">
                    <span className="text-muted-foreground">Proveedor</span>
                    <select value={provider} onChange={e => handleProviderChange(e.target.value)}
                        className="w-full px-3 py-2 rounded-lg bg-card border border-border text-foreground focus:outline-none focus:ring-2 focus:ring-purple-500 transition">
                        <option value="gmail">Gmail (App Password)</option>
                        <option value="outlook">Outlook / Microsoft 365</option>
                        <option value="yahoo">Yahoo Mail</option>
                        <option value="icloud">iCloud Mail</option>
                        <option value="custom">Servidor propio (custom)</option>
                    </select>
                </label>
                <label className="space-y-1.5 text-sm">
                    <span className="text-muted-foreground">Dirección de correo</span>
                    <input type="email" required value={emailAddr} onChange={e => setEmailAddr(e.target.value)}
                        placeholder="tu@correo.com" autoComplete="email"
                        className="w-full px-3 py-2 rounded-lg bg-card border border-border text-foreground focus:outline-none focus:ring-2 focus:ring-purple-500 transition" />
                </label>
            </div>
            <label className="space-y-1.5 text-sm block">
                <span className="text-muted-foreground">Contraseña</span>
                <input type="password" required value={password} onChange={e => setPassword(e.target.value)}
                    placeholder="App Password recomendado" autoComplete="off"
                    className="w-full px-3 py-2 rounded-lg bg-card border border-border text-foreground focus:outline-none focus:ring-2 focus:ring-purple-500 transition" />
                <span className="text-xs text-muted-foreground block leading-snug">{preset.help}</span>
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
                <label className="space-y-1.5 text-sm sm:col-span-3">
                    <span className="text-muted-foreground">Servidor IMAP</span>
                    <input type="text" value={imapHost} onChange={e => setImapHost(e.target.value)}
                        placeholder="imap.ejemplo.com"
                        className="w-full px-3 py-2 rounded-lg bg-card border border-border text-foreground focus:outline-none focus:ring-2 focus:ring-purple-500 transition" />
                </label>
                <label className="space-y-1.5 text-sm">
                    <span className="text-muted-foreground">Puerto IMAP</span>
                    <input type="number" value={imapPort} onChange={e => setImapPort(parseInt(e.target.value) || 0)}
                        className="w-full px-3 py-2 rounded-lg bg-card border border-border text-foreground focus:outline-none focus:ring-2 focus:ring-purple-500 transition" />
                </label>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
                <label className="space-y-1.5 text-sm sm:col-span-3">
                    <span className="text-muted-foreground">Servidor SMTP</span>
                    <input type="text" value={smtpHost} onChange={e => setSmtpHost(e.target.value)}
                        placeholder="smtp.ejemplo.com"
                        className="w-full px-3 py-2 rounded-lg bg-card border border-border text-foreground focus:outline-none focus:ring-2 focus:ring-purple-500 transition" />
                </label>
                <label className="space-y-1.5 text-sm">
                    <span className="text-muted-foreground">Puerto SMTP</span>
                    <input type="number" value={smtpPort} onChange={e => setSmtpPort(parseInt(e.target.value) || 0)}
                        className="w-full px-3 py-2 rounded-lg bg-card border border-border text-foreground focus:outline-none focus:ring-2 focus:ring-purple-500 transition" />
                </label>
            </div>
            <button type="submit" disabled={busy || !emailAddr.trim() || !password}
                className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-foreground text-sm font-medium transition">
                {busy ? <><Loader2 className="w-4 h-4 animate-spin" /> Verificando…</> : <><Plug className="w-4 h-4" /> Conectar correo</>}
            </button>
        </form>
    );
}

export default function IntegracionesPage() {
    const {
        loading, feedback,
        psd2Id, setPsd2Id, psd2Key, setPsd2Key,
        connectingPsd2, disconnectingPsd2,
        connectingGoogle, connectingMicrosoft,
        connectingEmail, disconnectingEmail,
        getStatus, isConnected,
        connectPsd2, disconnectPsd2, connectOAuth, disconnectIntegration,
        connectEmail, disconnectEmail,
    } = useIntegraciones();

    return (
        <div className="p-8 max-w-3xl mx-auto space-y-8">
            <div>
                <h1 className="text-2xl font-bold text-foreground">Integraciones</h1>
                <p className="text-sm text-muted-foreground mt-1 mb-6">
                    Conecta tus herramientas para que los agentes puedan actuar sobre ellas
                </p>
            </div>

            <InfoBanner id="integraciones-intro" title="Conecta tus servicios">
                <p>
                    Vincula tu banco, correo y almacenamiento para que los agentes puedan leer facturas,
                    enviar emails y sincronizar documentos automáticamente.
                    Las conexiones usan OAuth — <span className="text-primary">tus credenciales nunca se comparten con nosotros</span>.
                </p>
            </InfoBanner>

            {feedback && (
                <div className={`px-4 py-3 rounded-lg border text-sm ${feedback.type === "success"
                    ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                    : "bg-red-500/10 border-red-500/20 text-red-400"
                }`}>
                    {feedback.msg}
                </div>
            )}

            {/* Banco PSD2 */}
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
                        <p className="text-sm text-muted-foreground mb-4 leading-relaxed">
                            Para conectarte a tus cuentas bancarias usamos GoCardless (antes Nordigen), un agregador regulado bajo directiva <strong className="text-foreground">PSD2</strong> europea.
                        </p>
                        <div className="space-y-3">
                            <input type="text" required value={psd2Id} onChange={e => setPsd2Id(e.target.value)}
                                placeholder="Secret ID (puedes usar: DEMO_PSD2_ID)"
                                className="w-full px-4 py-2.5 rounded-lg bg-card border border-border text-foreground text-sm placeholder:text-muted-foreground font-mono focus:outline-none focus:ring-2 focus:ring-emerald-500 transition" />
                            <input type="password" required value={psd2Key} onChange={e => setPsd2Key(e.target.value)}
                                placeholder="Secret Key (puedes usar: DEMO_PSD2_ID)"
                                className="w-full px-4 py-2.5 rounded-lg bg-card border border-border text-foreground text-sm placeholder:text-muted-foreground font-mono focus:outline-none focus:ring-2 focus:ring-emerald-500 transition" />
                        </div>
                        <button type="submit" disabled={connectingPsd2 || !psd2Id.trim() || !psd2Key.trim()}
                            className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-foreground text-sm font-medium transition">
                            {connectingPsd2 ? <><Loader2 className="w-4 h-4 animate-spin" /> Verificando…</> : <><Plug className="w-4 h-4" /> Conectar PSD2</>}
                        </button>
                    </form>
                )}
            </IntegrationCard>

            {/* Gmail */}
            <IntegrationCard
                icon={<Mail className="w-5 h-5 text-red-400" />}
                iconBg="bg-red-500/10 border border-red-500/20"
                title="Gmail" subtitle="Correo electrónico con Google"
                loading={loading} connected={isConnected("gmail")}
                lastSync={getStatus("gmail")?.last_sync_at}
            >
                {isConnected("gmail") ? (
                    <div className="space-y-4">
                        <p className="text-sm text-muted-foreground">El agente de email puede leer y enviar correos desde tu cuenta de Gmail.</p>
                        <button onClick={() => disconnectIntegration("gmail", "Gmail")}
                            className="px-4 py-2 rounded-lg border border-red-500/30 text-red-400 hover:bg-red-500/10 text-sm transition">
                            Desconectar Gmail
                        </button>
                    </div>
                ) : (
                    <div className="space-y-4">
                        <p className="text-sm text-muted-foreground">Conecta tu cuenta de Gmail para que el agente pueda leer tu bandeja de entrada y enviar correos en tu nombre.</p>
                        <button onClick={() => connectOAuth("google")} disabled={connectingGoogle}
                            className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-red-600 hover:bg-red-500 disabled:opacity-50 text-foreground text-sm font-medium transition">
                            {connectingGoogle ? <><Loader2 className="w-4 h-4 animate-spin" /> Conectando…</> : <><Mail className="w-4 h-4" /> Conectar con Google</>}
                        </button>
                        <p className="text-xs text-muted-foreground">Al conectar Google se habilitan Gmail y Google Drive simultáneamente.</p>
                    </div>
                )}
            </IntegrationCard>

            {/* Google Drive */}
            <IntegrationCard
                icon={<HardDrive className="w-5 h-5 text-yellow-400" />}
                iconBg="bg-yellow-500/10 border border-yellow-500/20"
                title="Google Drive" subtitle="Almacenamiento y backup de documentos"
                loading={loading} connected={isConnected("gdrive")}
                lastSync={getStatus("gdrive")?.last_sync_at}
            >
                {isConnected("gdrive") ? (
                    <div className="space-y-4">
                        <p className="text-sm text-muted-foreground">
                            Sincroniza documentos, sube facturas y realiza backups automáticos en tu Google Drive.
                        </p>
                        <button onClick={() => disconnectIntegration("gdrive", "Google Drive")}
                            className="px-4 py-2 rounded-lg border border-red-500/30 text-red-400 hover:bg-red-500/10 text-sm transition">
                            Desconectar Google Drive
                        </button>
                    </div>
                ) : (
                    <div className="space-y-4">
                        <p className="text-sm text-muted-foreground">Conecta Google Drive para sincronizar documentos, exportar facturas y hacer backups automáticos.</p>
                        {isConnected("gmail") ? (
                            <p className="text-sm text-emerald-400/90 bg-emerald-500/10 px-4 py-3 border border-emerald-500/20 rounded-lg">
                                Google Drive ya está conectado junto con Gmail. Actívalo arriba.
                            </p>
                        ) : (
                            <button onClick={() => connectOAuth("google")} disabled={connectingGoogle}
                                className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-yellow-600 hover:bg-yellow-500 disabled:opacity-50 text-foreground text-sm font-medium transition">
                                {connectingGoogle ? <><Loader2 className="w-4 h-4 animate-spin" /> Conectando…</> : <><HardDrive className="w-4 h-4" /> Conectar con Google</>}
                            </button>
                        )}
                    </div>
                )}
            </IntegrationCard>

            {/* Outlook */}
            <IntegrationCard
                icon={<Mail className="w-5 h-5 text-blue-400" />}
                iconBg="bg-blue-500/10 border border-blue-500/20"
                title="Outlook" subtitle="Correo electrónico con Microsoft"
                loading={loading} connected={isConnected("outlook")}
                lastSync={getStatus("outlook")?.last_sync_at}
            >
                {isConnected("outlook") ? (
                    <div className="space-y-4">
                        <p className="text-sm text-muted-foreground">El agente de email puede leer y enviar correos desde tu cuenta de Outlook.</p>
                        <button onClick={() => disconnectIntegration("outlook", "Outlook")}
                            className="px-4 py-2 rounded-lg border border-red-500/30 text-red-400 hover:bg-red-500/10 text-sm transition">
                            Desconectar Outlook
                        </button>
                    </div>
                ) : (
                    <div className="space-y-4">
                        <p className="text-sm text-muted-foreground">Conecta tu cuenta de Outlook / Microsoft 365 para que el agente gestione tu correo.</p>
                        <button onClick={() => connectOAuth("microsoft")} disabled={connectingMicrosoft}
                            className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-foreground text-sm font-medium transition">
                            {connectingMicrosoft ? <><Loader2 className="w-4 h-4 animate-spin" /> Conectando…</> : <><Mail className="w-4 h-4" /> Conectar con Microsoft</>}
                        </button>
                        <p className="text-xs text-muted-foreground">Al conectar Microsoft se habilitan Outlook y OneDrive simultáneamente.</p>
                    </div>
                )}
            </IntegrationCard>

            {/* Email IMAP/SMTP (manual) */}
            <IntegrationCard
                icon={<Server className="w-5 h-5 text-purple-400" />}
                iconBg="bg-purple-500/10 border border-purple-500/20"
                title="Correo IMAP / SMTP" subtitle="Servidor propio, Yahoo, iCloud o fallback sin OAuth"
                loading={loading} connected={isConnected("email")}
                lastSync={getStatus("email")?.last_sync_at}
            >
                {isConnected("email") ? (
                    <div className="space-y-4">
                        <p className="text-sm text-muted-foreground">
                            Tu correo IMAP/SMTP está conectado. El agente de email puede leer la bandeja y enviar mensajes con adjuntos.
                        </p>
                        <button onClick={disconnectEmail} disabled={disconnectingEmail}
                            className="px-4 py-2 rounded-lg border border-red-500/30 text-red-400 hover:bg-red-500/10 disabled:opacity-50 text-sm transition">
                            {disconnectingEmail ? "Desconectando…" : "Desconectar correo"}
                        </button>
                    </div>
                ) : (
                    <EmailSmtpForm onSubmit={connectEmail} busy={connectingEmail} />
                )}
            </IntegrationCard>

            {/* OneDrive */}
            <IntegrationCard
                icon={<Cloud className="w-5 h-5 text-sky-400" />}
                iconBg="bg-sky-500/10 border border-sky-500/20"
                title="Microsoft 365 / OneDrive" subtitle="Almacenamiento y backup de documentos"
                loading={loading} connected={isConnected("onedrive")}
                lastSync={getStatus("onedrive")?.last_sync_at}
            >
                {isConnected("onedrive") ? (
                    <div className="space-y-4">
                        <p className="text-sm text-muted-foreground">
                            Sincroniza documentos, sube facturas y realiza backups automáticos en tu OneDrive.
                        </p>
                        <button onClick={() => disconnectIntegration("onedrive", "OneDrive")}
                            className="px-4 py-2 rounded-lg border border-red-500/30 text-red-400 hover:bg-red-500/10 text-sm transition">
                            Desconectar OneDrive
                        </button>
                    </div>
                ) : (
                    <div className="space-y-4">
                        <p className="text-sm text-muted-foreground">Conecta OneDrive para sincronizar documentos, exportar facturas y hacer backups automáticos.</p>
                        {isConnected("outlook") ? (
                            <p className="text-sm text-emerald-400/90 bg-emerald-500/10 px-4 py-3 border border-emerald-500/20 rounded-lg">
                                OneDrive ya está conectado junto con Outlook. Actívalo arriba.
                            </p>
                        ) : (
                            <button onClick={() => connectOAuth("microsoft")} disabled={connectingMicrosoft}
                                className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-foreground text-sm font-medium transition">
                                {connectingMicrosoft ? <><Loader2 className="w-4 h-4 animate-spin" /> Conectando…</> : <><Cloud className="w-4 h-4" /> Conectar con Microsoft</>}
                            </button>
                        )}
                    </div>
                )}
            </IntegrationCard>
        </div>
    );
}
