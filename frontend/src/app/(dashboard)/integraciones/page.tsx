"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { CheckCircle2, XCircle, Loader2, Plug, Building2, Mail, Cloud, HardDrive, Server } from "lucide-react";
import InfoBanner from "@/components/InfoBanner";
import { useIntegraciones } from "./_hooks/useIntegraciones";

const SMTP_PRESETS: Record<string, { imap_host: string; imap_port: number; smtp_host: string; smtp_port: number; helpKey: string }> = {
    gmail: { imap_host: "imap.gmail.com", imap_port: 993, smtp_host: "smtp.gmail.com", smtp_port: 587, helpKey: "email.help.gmail" },
    outlook: { imap_host: "outlook.office365.com", imap_port: 993, smtp_host: "smtp.office365.com", smtp_port: 587, helpKey: "email.help.outlook" },
    yahoo: { imap_host: "imap.mail.yahoo.com", imap_port: 993, smtp_host: "smtp.mail.yahoo.com", smtp_port: 587, helpKey: "email.help.yahoo" },
    icloud: { imap_host: "imap.mail.me.com", imap_port: 993, smtp_host: "smtp.mail.me.com", smtp_port: 587, helpKey: "email.help.icloud" },
    custom: { imap_host: "", imap_port: 993, smtp_host: "", smtp_port: 587, helpKey: "email.help.custom" },
};

function StatusBadge({ loading, connected }: { loading: boolean; connected: boolean }) {
    const t = useTranslations("integraciones");
    if (loading) return <Loader2 className="w-4 h-4 text-muted-foreground animate-spin" />;
    if (connected) return <div className="flex items-center gap-2 text-emerald-400 text-sm"><CheckCircle2 className="w-4 h-4" /> {t("status.connected")}</div>;
    return <div className="flex items-center gap-2 text-muted-foreground text-sm"><XCircle className="w-4 h-4" /> {t("status.notConnected")}</div>;
}

function IntegrationCard({
    icon, iconBg, title, subtitle, loading, connected, lastSync, children,
}: {
    icon: React.ReactNode; iconBg: string; title: string; subtitle: string;
    loading: boolean; connected: boolean; lastSync?: string; children: React.ReactNode;
}) {
    const t = useTranslations("integraciones");
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
                        {t("card.lastSync", { date: new Date(lastSync).toLocaleString("es-ES") })}
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
    const t = useTranslations("integraciones");
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
                {t("email.intro.before")} <strong className="text-foreground">Gmail</strong> {t("email.intro.and")} <strong className="text-foreground">Outlook</strong> {t("email.intro.after")}
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <label className="space-y-1.5 text-sm">
                    <span className="text-muted-foreground">{t("email.fields.provider")}</span>
                    <select value={provider} onChange={e => handleProviderChange(e.target.value)}
                        className="w-full px-3 py-2 rounded-lg bg-card border border-border text-foreground focus:outline-none focus:ring-2 focus:ring-purple-500 transition">
                        <option value="gmail">{t("email.providers.gmail")}</option>
                        <option value="outlook">{t("email.providers.outlook")}</option>
                        <option value="yahoo">{t("email.providers.yahoo")}</option>
                        <option value="icloud">{t("email.providers.icloud")}</option>
                        <option value="custom">{t("email.providers.custom")}</option>
                    </select>
                </label>
                <label className="space-y-1.5 text-sm">
                    <span className="text-muted-foreground">{t("email.fields.address")}</span>
                    <input type="email" required value={emailAddr} onChange={e => setEmailAddr(e.target.value)}
                        placeholder={t("email.fields.addressPlaceholder")} autoComplete="email"
                        className="w-full px-3 py-2 rounded-lg bg-card border border-border text-foreground focus:outline-none focus:ring-2 focus:ring-purple-500 transition" />
                </label>
            </div>
            <label className="space-y-1.5 text-sm block">
                <span className="text-muted-foreground">{t("email.fields.password")}</span>
                <input type="password" required value={password} onChange={e => setPassword(e.target.value)}
                    placeholder={t("email.fields.passwordPlaceholder")} autoComplete="off"
                    className="w-full px-3 py-2 rounded-lg bg-card border border-border text-foreground focus:outline-none focus:ring-2 focus:ring-purple-500 transition" />
                <span className="text-xs text-muted-foreground block leading-snug">{t(preset.helpKey)}</span>
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
                <label className="space-y-1.5 text-sm sm:col-span-3">
                    <span className="text-muted-foreground">{t("email.fields.imapHost")}</span>
                    <input type="text" value={imapHost} onChange={e => setImapHost(e.target.value)}
                        placeholder={t("email.fields.imapHostPlaceholder")}
                        className="w-full px-3 py-2 rounded-lg bg-card border border-border text-foreground focus:outline-none focus:ring-2 focus:ring-purple-500 transition" />
                </label>
                <label className="space-y-1.5 text-sm">
                    <span className="text-muted-foreground">{t("email.fields.imapPort")}</span>
                    <input type="number" value={imapPort} onChange={e => setImapPort(parseInt(e.target.value) || 0)}
                        className="w-full px-3 py-2 rounded-lg bg-card border border-border text-foreground focus:outline-none focus:ring-2 focus:ring-purple-500 transition" />
                </label>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
                <label className="space-y-1.5 text-sm sm:col-span-3">
                    <span className="text-muted-foreground">{t("email.fields.smtpHost")}</span>
                    <input type="text" value={smtpHost} onChange={e => setSmtpHost(e.target.value)}
                        placeholder={t("email.fields.smtpHostPlaceholder")}
                        className="w-full px-3 py-2 rounded-lg bg-card border border-border text-foreground focus:outline-none focus:ring-2 focus:ring-purple-500 transition" />
                </label>
                <label className="space-y-1.5 text-sm">
                    <span className="text-muted-foreground">{t("email.fields.smtpPort")}</span>
                    <input type="number" value={smtpPort} onChange={e => setSmtpPort(parseInt(e.target.value) || 0)}
                        className="w-full px-3 py-2 rounded-lg bg-card border border-border text-foreground focus:outline-none focus:ring-2 focus:ring-purple-500 transition" />
                </label>
            </div>
            <button type="submit" disabled={busy || !emailAddr.trim() || !password}
                className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-foreground text-sm font-medium transition">
                {busy ? <><Loader2 className="w-4 h-4 animate-spin" /> {t("email.verifying")}</> : <><Plug className="w-4 h-4" /> {t("email.connect")}</>}
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
    const t = useTranslations("integraciones");

    return (
        <div className="p-8 max-w-3xl mx-auto space-y-8">
            <div>
                <h1 className="text-2xl font-bold text-foreground">{t("title")}</h1>
                <p className="text-sm text-muted-foreground mt-1 mb-6">
                    {t("subtitle")}
                </p>
            </div>

            <InfoBanner id="integraciones-intro" title={t("banner.title")}>
                <p>
                    {t("banner.before")} <span className="text-primary">{t("banner.highlight")}</span>.
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
                title={t("psd2.title")} subtitle={t("psd2.subtitle")}
                loading={loading} connected={isConnected("psd2")}
                lastSync={getStatus("psd2")?.last_sync_at}
            >
                {isConnected("psd2") ? (
                    <div className="space-y-4">
                        <p className="text-sm text-emerald-400/90 bg-emerald-500/10 px-4 py-3 border border-emerald-500/20 rounded-lg">
                            {t("psd2.connectedInfo")}
                        </p>
                        <button onClick={disconnectPsd2} disabled={disconnectingPsd2}
                            className="px-4 py-2 rounded-lg border border-red-500/30 text-red-400 hover:bg-red-500/10 disabled:opacity-50 text-sm transition">
                            {disconnectingPsd2 ? t("actions.disconnecting") : t("psd2.disconnect")}
                        </button>
                    </div>
                ) : (
                    <form onSubmit={connectPsd2} className="space-y-4">
                        <p className="text-sm text-muted-foreground mb-4 leading-relaxed">
                            {t("psd2.intro.before")} <strong className="text-foreground">PSD2</strong> {t("psd2.intro.after")}
                        </p>
                        <div className="space-y-3">
                            <input type="text" required value={psd2Id} onChange={e => setPsd2Id(e.target.value)}
                                placeholder={t("psd2.secretIdPlaceholder")}
                                className="w-full px-4 py-2.5 rounded-lg bg-card border border-border text-foreground text-sm placeholder:text-muted-foreground font-mono focus:outline-none focus:ring-2 focus:ring-emerald-500 transition" />
                            <input type="password" required value={psd2Key} onChange={e => setPsd2Key(e.target.value)}
                                placeholder={t("psd2.secretKeyPlaceholder")}
                                className="w-full px-4 py-2.5 rounded-lg bg-card border border-border text-foreground text-sm placeholder:text-muted-foreground font-mono focus:outline-none focus:ring-2 focus:ring-emerald-500 transition" />
                        </div>
                        <button type="submit" disabled={connectingPsd2 || !psd2Id.trim() || !psd2Key.trim()}
                            className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-foreground text-sm font-medium transition">
                            {connectingPsd2 ? <><Loader2 className="w-4 h-4 animate-spin" /> {t("email.verifying")}</> : <><Plug className="w-4 h-4" /> {t("psd2.connect")}</>}
                        </button>
                    </form>
                )}
            </IntegrationCard>

            {/* Gmail */}
            <IntegrationCard
                icon={<Mail className="w-5 h-5 text-red-400" />}
                iconBg="bg-red-500/10 border border-red-500/20"
                title="Gmail" subtitle={t("gmail.subtitle")}
                loading={loading} connected={isConnected("gmail")}
                lastSync={getStatus("gmail")?.last_sync_at}
            >
                {isConnected("gmail") ? (
                    <div className="space-y-4">
                        <p className="text-sm text-muted-foreground">{t("gmail.connectedInfo")}</p>
                        <button onClick={() => disconnectIntegration("gmail", "Gmail")}
                            className="px-4 py-2 rounded-lg border border-red-500/30 text-red-400 hover:bg-red-500/10 text-sm transition">
                            {t("gmail.disconnect")}
                        </button>
                    </div>
                ) : (
                    <div className="space-y-4">
                        <p className="text-sm text-muted-foreground">{t("gmail.intro")}</p>
                        <button onClick={() => connectOAuth("google")} disabled={connectingGoogle}
                            className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-red-600 hover:bg-red-500 disabled:opacity-50 text-foreground text-sm font-medium transition">
                            {connectingGoogle ? <><Loader2 className="w-4 h-4 animate-spin" /> {t("actions.connecting")}</> : <><Mail className="w-4 h-4" /> {t("actions.connectGoogle")}</>}
                        </button>
                        <p className="text-xs text-muted-foreground">{t("gmail.oauthNote")}</p>
                    </div>
                )}
            </IntegrationCard>

            {/* Google Drive */}
            <IntegrationCard
                icon={<HardDrive className="w-5 h-5 text-yellow-400" />}
                iconBg="bg-yellow-500/10 border border-yellow-500/20"
                title="Google Drive" subtitle={t("gdrive.subtitle")}
                loading={loading} connected={isConnected("gdrive")}
                lastSync={getStatus("gdrive")?.last_sync_at}
            >
                {isConnected("gdrive") ? (
                    <div className="space-y-4">
                        <p className="text-sm text-muted-foreground">
                            {t("gdrive.connectedInfo")}
                        </p>
                        <button onClick={() => disconnectIntegration("gdrive", "Google Drive")}
                            className="px-4 py-2 rounded-lg border border-red-500/30 text-red-400 hover:bg-red-500/10 text-sm transition">
                            {t("gdrive.disconnect")}
                        </button>
                    </div>
                ) : (
                    <div className="space-y-4">
                        <p className="text-sm text-muted-foreground">{t("gdrive.intro")}</p>
                        {isConnected("gmail") ? (
                            <p className="text-sm text-emerald-400/90 bg-emerald-500/10 px-4 py-3 border border-emerald-500/20 rounded-lg">
                                {t("gdrive.alreadyWithGmail")}
                            </p>
                        ) : (
                            <button onClick={() => connectOAuth("google")} disabled={connectingGoogle}
                                className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-yellow-600 hover:bg-yellow-500 disabled:opacity-50 text-foreground text-sm font-medium transition">
                                {connectingGoogle ? <><Loader2 className="w-4 h-4 animate-spin" /> {t("actions.connecting")}</> : <><HardDrive className="w-4 h-4" /> {t("actions.connectGoogle")}</>}
                            </button>
                        )}
                    </div>
                )}
            </IntegrationCard>

            {/* Outlook */}
            <IntegrationCard
                icon={<Mail className="w-5 h-5 text-blue-400" />}
                iconBg="bg-blue-500/10 border border-blue-500/20"
                title="Outlook" subtitle={t("outlook.subtitle")}
                loading={loading} connected={isConnected("outlook")}
                lastSync={getStatus("outlook")?.last_sync_at}
            >
                {isConnected("outlook") ? (
                    <div className="space-y-4">
                        <p className="text-sm text-muted-foreground">{t("outlook.connectedInfo")}</p>
                        <button onClick={() => disconnectIntegration("outlook", "Outlook")}
                            className="px-4 py-2 rounded-lg border border-red-500/30 text-red-400 hover:bg-red-500/10 text-sm transition">
                            {t("outlook.disconnect")}
                        </button>
                    </div>
                ) : (
                    <div className="space-y-4">
                        <p className="text-sm text-muted-foreground">{t("outlook.intro")}</p>
                        <button onClick={() => connectOAuth("microsoft")} disabled={connectingMicrosoft}
                            className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-foreground text-sm font-medium transition">
                            {connectingMicrosoft ? <><Loader2 className="w-4 h-4 animate-spin" /> {t("actions.connecting")}</> : <><Mail className="w-4 h-4" /> {t("actions.connectMicrosoft")}</>}
                        </button>
                        <p className="text-xs text-muted-foreground">{t("outlook.oauthNote")}</p>
                    </div>
                )}
            </IntegrationCard>

            {/* Email IMAP/SMTP (manual) */}
            <IntegrationCard
                icon={<Server className="w-5 h-5 text-purple-400" />}
                iconBg="bg-purple-500/10 border border-purple-500/20"
                title={t("email.title")} subtitle={t("email.subtitle")}
                loading={loading} connected={isConnected("email")}
                lastSync={getStatus("email")?.last_sync_at}
            >
                {isConnected("email") ? (
                    <div className="space-y-4">
                        <p className="text-sm text-muted-foreground">
                            {t("email.connectedInfo")}
                        </p>
                        <button onClick={disconnectEmail} disabled={disconnectingEmail}
                            className="px-4 py-2 rounded-lg border border-red-500/30 text-red-400 hover:bg-red-500/10 disabled:opacity-50 text-sm transition">
                            {disconnectingEmail ? t("actions.disconnecting") : t("email.disconnect")}
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
                title="Microsoft 365 / OneDrive" subtitle={t("onedrive.subtitle")}
                loading={loading} connected={isConnected("onedrive")}
                lastSync={getStatus("onedrive")?.last_sync_at}
            >
                {isConnected("onedrive") ? (
                    <div className="space-y-4">
                        <p className="text-sm text-muted-foreground">
                            {t("onedrive.connectedInfo")}
                        </p>
                        <button onClick={() => disconnectIntegration("onedrive", "OneDrive")}
                            className="px-4 py-2 rounded-lg border border-red-500/30 text-red-400 hover:bg-red-500/10 text-sm transition">
                            {t("onedrive.disconnect")}
                        </button>
                    </div>
                ) : (
                    <div className="space-y-4">
                        <p className="text-sm text-muted-foreground">{t("onedrive.intro")}</p>
                        {isConnected("outlook") ? (
                            <p className="text-sm text-emerald-400/90 bg-emerald-500/10 px-4 py-3 border border-emerald-500/20 rounded-lg">
                                {t("onedrive.alreadyWithOutlook")}
                            </p>
                        ) : (
                            <button onClick={() => connectOAuth("microsoft")} disabled={connectingMicrosoft}
                                className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-foreground text-sm font-medium transition">
                                {connectingMicrosoft ? <><Loader2 className="w-4 h-4 animate-spin" /> {t("actions.connecting")}</> : <><Cloud className="w-4 h-4" /> {t("actions.connectMicrosoft")}</>}
                            </button>
                        )}
                    </div>
                )}
            </IntegrationCard>
        </div>
    );
}
