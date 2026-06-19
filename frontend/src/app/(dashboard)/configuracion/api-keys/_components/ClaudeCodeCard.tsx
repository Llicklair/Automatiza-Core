import { useTranslations } from "next-intl";
import { CheckCircle2, Loader2, Terminal } from "lucide-react";
import { api } from "@/lib/api";
import type { ClaudeSetupState, ProviderState } from "../_hooks/useApiKeys";

interface ClaudeCodeCardProps {
    claudeSetup: ClaudeSetupState;
    setClaudeSetup: (v: ClaudeSetupState | ((s: ClaudeSetupState) => ClaudeSetupState)) => void;
    updateProvider: (key: string, patch: Partial<ProviderState>) => void;
}

export function ClaudeCodeCard({ claudeSetup, setClaudeSetup, updateProvider }: ClaudeCodeCardProps) {
    const t = useTranslations("configuracion");
    const tc = useTranslations("common");
    return (
        <div className="bg-card border border-border rounded-2xl p-6 mb-4">
            <h2 className="text-base font-bold text-foreground flex items-center gap-2 mb-1">
                <Terminal className="w-4 h-4 text-primary" /> {t("apiKeys.claudeCodeTitle")}
            </h2>
            <p className="text-xs text-muted-foreground mb-4">
                {t("apiKeys.claudeCodeDesc")}
            </p>

            {/* Checking */}
            {claudeSetup.phase === "checking" && (
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Loader2 className="w-4 h-4 animate-spin text-primary" />
                    {t("apiKeys.verifying")}
                </div>
            )}

            {/* Ready */}
            {claudeSetup.phase === "ready" && (
                <div className="space-y-3">
                    <div className="flex items-center justify-between p-3 rounded-xl border border-emerald-500/30 bg-emerald-500/5">
                        <div className="flex items-center gap-2">
                            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                            <span className="text-sm font-medium text-emerald-300">{t("apiKeys.connected")}</span>
                            {claudeSetup.version && (
                                <span className="text-[10px] text-emerald-500 font-mono">v{claudeSetup.version}</span>
                            )}
                        </div>
                        <button
                            onClick={async () => {
                                setClaudeSetup({ phase: "checking" });
                                try {
                                    const res = await api.tenant.logoutClaudeCode();
                                    setClaudeSetup({ phase: res.status === "error" ? "error" : "idle", message: res.message });
                                } catch (e: any) {
                                    setClaudeSetup({ phase: "error", message: e?.message || tc("error") });
                                }
                            }}
                            className="text-[11px] px-3 py-1.5 rounded-lg border border-rose-500/30 text-rose-400 hover:bg-rose-500/10 transition"
                        >
                            {t("apiKeys.logout")}
                        </button>
                    </div>
                </div>
            )}

            {/* Needs auth */}
            {claudeSetup.phase === "needs_auth" && (
                <div className="space-y-3">
                    <div className="p-3 rounded-xl border border-amber-500/30 bg-amber-500/5">
                        <div className="flex items-center gap-2">
                            <Terminal className="w-4 h-4 text-amber-400" />
                            <span className="text-sm font-medium text-amber-300">
                                {t("apiKeys.cliInstalledNotLoggedIn", { version: claudeSetup.version ? ` (v${claudeSetup.version})` : "" })}
                            </span>
                        </div>
                    </div>
                    <div className="flex gap-2">
                        <button
                            onClick={async () => {
                                setClaudeSetup(s => ({ ...s, phase: "checking" }));
                                try {
                                    const res = await api.tenant.loginClaudeCode();
                                    setClaudeSetup({ phase: "needs_auth", version: claudeSetup.version, message: res.message });
                                } catch (e: any) {
                                    setClaudeSetup({ phase: "error", message: e?.message || tc("error") });
                                }
                            }}
                            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-primary hover:bg-primary text-foreground text-xs font-medium transition"
                        >
                            <Terminal className="w-3.5 h-3.5" />
                            {t("apiKeys.login")}
                        </button>
                        <button
                            onClick={async () => {
                                setClaudeSetup(s => ({ ...s, phase: "checking" }));
                                try {
                                    const res = await api.tenant.setupClaudeCode();
                                    if (res.status === "ready") {
                                        setClaudeSetup({ phase: "ready", version: res.version, message: res.message });
                                        updateProvider("claude_code", { enabled: true });
                                    } else if (res.status === "needs_auth") {
                                        setClaudeSetup({ phase: "needs_auth", version: res.version, message: res.message });
                                    } else {
                                        setClaudeSetup({ phase: "error", message: res.message });
                                    }
                                } catch (e: any) {
                                    setClaudeSetup({ phase: "error", message: e?.message || tc("error") });
                                }
                            }}
                            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg border border-primary/20 text-primary hover:bg-primary/10 text-xs font-medium transition"
                        >
                            {t("apiKeys.verifyConnection")}
                        </button>
                    </div>
                    {claudeSetup.message && (
                        <p className="text-[11px] text-muted-foreground">{claudeSetup.message}</p>
                    )}
                </div>
            )}

            {/* Idle */}
            {claudeSetup.phase === "idle" && (
                <div className="space-y-3">
                    <p className="text-[11px] text-muted-foreground">
                        {t.rich("apiKeys.idleHint", {
                            nodeLink: (chunks) => <a href="https://nodejs.org/" target="_blank" rel="noopener noreferrer" className="text-primary hover:text-primary underline">{chunks}</a>,
                        })}
                    </p>
                    <div className="flex gap-2">
                        <button
                            onClick={async () => {
                                setClaudeSetup({ phase: "checking" });
                                try {
                                    const setupRes = await api.tenant.setupClaudeCode();
                                    if (setupRes.status === "ready") {
                                        setClaudeSetup({ phase: "ready", version: setupRes.version, message: setupRes.message });
                                        updateProvider("claude_code", { enabled: true });
                                        return;
                                    }
                                    const loginRes = await api.tenant.loginClaudeCode();
                                    setClaudeSetup({ phase: "needs_auth", version: setupRes.version, message: loginRes.message });
                                } catch (e: any) {
                                    setClaudeSetup({ phase: "error", message: e?.message || tc("error") });
                                }
                            }}
                            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-primary hover:bg-primary text-foreground text-xs font-medium transition"
                        >
                            <Terminal className="w-3.5 h-3.5" />
                            {t("apiKeys.login")}
                        </button>
                        <button
                            onClick={async () => {
                                setClaudeSetup({ phase: "checking" });
                                try {
                                    const res = await api.tenant.setupClaudeCode();
                                    if (res.status === "ready") {
                                        setClaudeSetup({ phase: "ready", version: res.version, message: res.message });
                                        updateProvider("claude_code", { enabled: true });
                                    } else if (res.status === "needs_auth") {
                                        setClaudeSetup({ phase: "needs_auth", version: res.version, message: res.message });
                                    } else {
                                        setClaudeSetup({ phase: "error", message: res.message });
                                    }
                                } catch (e: any) {
                                    setClaudeSetup({ phase: "error", message: e?.message || tc("error") });
                                }
                            }}
                            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg border border-primary/20 text-primary hover:bg-primary/10 text-xs font-medium transition"
                        >
                            {t("apiKeys.verifyConnection")}
                        </button>
                    </div>
                    {claudeSetup.message && (
                        <p className="text-[11px] text-muted-foreground">{claudeSetup.message}</p>
                    )}
                </div>
            )}

            {/* Error */}
            {claudeSetup.phase === "error" && (
                <div className="space-y-2">
                    <div className="p-3 rounded-xl border border-rose-500/30 bg-rose-500/5">
                        <p className="text-xs text-rose-400">{claudeSetup.message}</p>
                    </div>
                    <button
                        onClick={() => setClaudeSetup({ phase: "idle" })}
                        className="text-[11px] text-primary hover:text-primary underline transition"
                    >
                        {t("apiKeys.retry")}
                    </button>
                </div>
            )}
        </div>
    );
}
