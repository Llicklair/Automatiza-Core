/**
 * PRES.REG — wizard onboarding REGAP (apoderamiento AEAT).
 *
 * Tres ramas (Cl@ve PIN / Cl@ve Permanente / Cert FNMT) más verificación
 * final contra REGAP. Los endpoints del backend son reales, pero la consulta
 * REGAP sigue mockeada en el servidor (services/onboarding/regap.py, pendiente
 * del alta como colaborador social AEAT) — la UI ya está completa: activar la
 * consulta real será solo un cambio en el backend.
 */
"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import {
    AlertCircle,
    CheckCircle2,
    ExternalLink,
    KeyRound,
    Loader2,
    RefreshCw,
    ShieldCheck,
} from "lucide-react";
import { api } from "@/lib/api";
import type { RegapAuthMethod, RegapStatus } from "@/lib/api/regap";
import { useToastStore } from "@/stores/toast";

// Deep-links oficiales — URLs públicas estables de AEAT/FNMT.
const URL_CLAVE_REGISTRO = "https://clave.gob.es/clave_Home/registro.html";
const URL_CLAVE_AEAT = "https://sede.agenciatributaria.gob.es";
const URL_FNMT_PERSONA_FISICA = "https://www.sede.fnmt.gob.es/certificados/persona-fisica";
const URL_REGAP_OTORGAR =
    "https://sede.agenciatributaria.gob.es/Sede/Inicio/_otros_/Apoderamiento/Apoderamientos.html";

type Branch = "tiene_clave" | "quiere_clave" | "quiere_cert_fnmt";

export function ApoderamientoPanel() {
    const t = useTranslations("configuracion");
    const [status, setStatus] = useState<RegapStatus | null>(null);
    const [loading, setLoading] = useState(true);
    const [busy, setBusy] = useState(false);
    const [branch, setBranch] = useState<Branch | null>(null);
    const [nifCliente, setNifCliente] = useState("");
    const toast = useToastStore();

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const res = await api.regap.get();
            setStatus(res);
        } catch (e: any) {
            toast.show(`${t("verifactu.errorLoadingRegap")}: ${e.message}`, "error");
        } finally {
            setLoading(false);
        }
    }, [toast, t]);

    useEffect(() => {
        load();
    }, [load]);

    async function handleStartBranch(b: Branch) {
        const method: RegapAuthMethod =
            b === "tiene_clave"
                ? "clave_permanente"
                : b === "quiere_clave"
                    ? "clave_pin"
                    : "cert_fnmt";
        setBranch(b);
        setBusy(true);
        try {
            const updated = await api.regap.start(method);
            setStatus(updated);
        } catch (e: any) {
            toast.show(`${t("verifactu.errorPrefix")}: ${e.message}`, "error");
        } finally {
            setBusy(false);
        }
    }

    async function handleGrant() {
        setBusy(true);
        try {
            const updated = await api.regap.grant();
            setStatus(updated);
        } catch (e: any) {
            toast.show(`${t("verifactu.errorPrefix")}: ${e.message}`, "error");
        } finally {
            setBusy(false);
        }
    }

    async function handleVerify() {
        if (!nifCliente.trim()) {
            toast.show(t("verifactu.enterClientNif"), "warning");
            return;
        }
        setBusy(true);
        try {
            const updated = await api.regap.verify(nifCliente.trim().toUpperCase());
            setStatus(updated);
            if (updated.status === "verified") {
                toast.show(t("verifactu.poaVerifiedToast"), "success");
            } else if (updated.status === "rejected") {
                toast.show(t("verifactu.poaNotFoundToast"), "error");
            }
        } catch (e: any) {
            toast.show(`${t("verifactu.errorPrefix")}: ${e.message}`, "error");
        } finally {
            setBusy(false);
        }
    }

    async function handleReset() {
        setBusy(true);
        try {
            const updated = await api.regap.reset();
            setStatus(updated);
            setBranch(null);
            setNifCliente("");
        } catch (e: any) {
            toast.show(`${t("verifactu.errorPrefix")}: ${e.message}`, "error");
        } finally {
            setBusy(false);
        }
    }

    if (loading) {
        return (
            <div className="p-8 flex items-center gap-3 text-muted-foreground">
                <Loader2 className="w-4 h-4 animate-spin" /> {t("verifactu.loadingRegap")}
            </div>
        );
    }

    const phase = status?.status ?? "not_started";
    const apoderado = status?.apoderado_nombre ?? "AutomatizaCore S.L.";

    return (
        <div className="space-y-6">
            <header>
                <h1 className="text-2xl font-semibold text-foreground tracking-tight">
                    {t("verifactu.poaTitle")}
                </h1>
                <p className="mt-1 text-sm text-muted-foreground">
                    {t.rich("verifactu.poaIntro", {
                        apoderado,
                        strong: (chunks) => <strong>{chunks}</strong>,
                    })}
                </p>
            </header>

            <PhaseStepper current={phase} />

            {phase === "not_started" && (
                <section aria-labelledby="branch-heading" className="space-y-4">
                    <h2 id="branch-heading" className="text-lg font-medium text-foreground">
                        {t("verifactu.howIdentify")}
                    </h2>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        <BranchCard
                            icon={<KeyRound className="w-5 h-5 text-primary" />}
                            title={t("verifactu.branchHaveClaveTitle")}
                            description={t("verifactu.branchHaveClaveDesc")}
                            onClick={() => handleStartBranch("tiene_clave")}
                            disabled={busy}
                        />
                        <BranchCard
                            icon={<KeyRound className="w-5 h-5 text-primary" />}
                            title={t("verifactu.branchWantClaveTitle")}
                            description={t("verifactu.branchWantClaveDesc")}
                            onClick={() => handleStartBranch("quiere_clave")}
                            disabled={busy}
                        />
                        <BranchCard
                            icon={<ShieldCheck className="w-5 h-5 text-primary" />}
                            title={t("verifactu.branchWantCertTitle")}
                            description={t("verifactu.branchWantCertDesc")}
                            onClick={() => handleStartBranch("quiere_cert_fnmt")}
                            disabled={busy}
                        />
                    </div>
                </section>
            )}

            {(phase === "identifying" || phase === "cert_pending") && (
                <section aria-labelledby="instruct-heading" className="space-y-4">
                    <h2 id="instruct-heading" className="text-lg font-medium text-foreground">
                        {t("verifactu.step2Title")}
                    </h2>

                    {status?.auth_method === "cert_fnmt" && (
                        <Instructions
                            steps={[
                                {
                                    text: t("verifactu.certStep1Text"),
                                    href: URL_FNMT_PERSONA_FISICA,
                                    cta: t("verifactu.ctaRequestFnmt"),
                                },
                                {
                                    text: t("verifactu.certStep2Text"),
                                    detail: t("verifactu.poaDetail", { nif: status.apoderado_nif ?? "", apoderado }),
                                    href: URL_REGAP_OTORGAR,
                                    cta: t("verifactu.ctaGrantRegap"),
                                },
                                {
                                    text: t("verifactu.certStep3Text"),
                                },
                            ]}
                        />
                    )}

                    {status?.auth_method === "clave_pin" && (
                        <Instructions
                            steps={[
                                {
                                    text: t("verifactu.pinStep1Text"),
                                    href: URL_CLAVE_REGISTRO,
                                    cta: t("verifactu.ctaRegisterClave"),
                                },
                                {
                                    text: t("verifactu.pinStep2Text"),
                                    detail: t("verifactu.poaDetail", { nif: status.apoderado_nif ?? "", apoderado }),
                                    href: URL_REGAP_OTORGAR,
                                    cta: t("verifactu.ctaGrantRegap"),
                                },
                                {
                                    text: t("verifactu.markProcedure"),
                                },
                            ]}
                        />
                    )}

                    {status?.auth_method === "clave_permanente" && (
                        <Instructions
                            steps={[
                                {
                                    text: t("verifactu.permStep1Text"),
                                    href: URL_CLAVE_AEAT,
                                    cta: t("verifactu.ctaOpenAeat"),
                                },
                                {
                                    text: t("verifactu.permStep2Text"),
                                    detail: t("verifactu.poaDetail", { nif: status?.apoderado_nif ?? "", apoderado }),
                                    href: URL_REGAP_OTORGAR,
                                    cta: t("verifactu.ctaGrantRegap"),
                                },
                                {
                                    text: t("verifactu.markProcedure"),
                                },
                            ]}
                        />
                    )}

                    <div className="flex items-center gap-3 pt-2 border-t border-border">
                        <button
                            type="button"
                            onClick={handleGrant}
                            disabled={busy}
                            className="px-4 py-2 rounded-md bg-primary text-foreground text-sm font-medium hover:bg-primary/90 disabled:opacity-50 flex items-center gap-2"
                        >
                            {busy && <Loader2 className="w-4 h-4 animate-spin" />}
                            {t("verifactu.poaCompleted")}
                        </button>
                        <button
                            type="button"
                            onClick={handleReset}
                            disabled={busy}
                            className="px-3 py-2 rounded-md text-sm text-muted-foreground hover:text-foreground flex items-center gap-1.5"
                        >
                            <RefreshCw className="w-3.5 h-3.5" /> {t("verifactu.changeMethod")}
                        </button>
                    </div>
                </section>
            )}

            {phase === "power_granted" && (
                <section aria-labelledby="verify-heading" className="space-y-4">
                    <h2 id="verify-heading" className="text-lg font-medium text-foreground">
                        {t("verifactu.step3Title")}
                    </h2>
                    <p className="text-sm text-muted-foreground">
                        {t("verifactu.step3Desc")}
                    </p>
                    <div>
                        <label htmlFor="nif-cliente" className="block text-sm font-medium text-foreground mb-1.5">
                            {t("verifactu.clientNifLabel")}
                        </label>
                        <input
                            id="nif-cliente"
                            type="text"
                            value={nifCliente}
                            onChange={(e) => setNifCliente(e.target.value)}
                            placeholder="B12345678 o 12345678Z"
                            className="w-full max-w-xs px-3 py-2 rounded-md bg-background border border-border text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                        />
                    </div>
                    <div className="flex items-center gap-3">
                        <button
                            type="button"
                            onClick={handleVerify}
                            disabled={busy}
                            className="px-4 py-2 rounded-md bg-primary text-foreground text-sm font-medium hover:bg-primary/90 disabled:opacity-50 flex items-center gap-2"
                        >
                            {busy && <Loader2 className="w-4 h-4 animate-spin" />}
                            {t("verifactu.queryRegap")}
                        </button>
                        <button
                            type="button"
                            onClick={handleReset}
                            disabled={busy}
                            className="px-3 py-2 rounded-md text-sm text-muted-foreground hover:text-foreground"
                        >
                            {t("verifactu.restartWizard")}
                        </button>
                    </div>
                </section>
            )}

            {phase === "verified" && (
                <section
                    aria-labelledby="verified-heading"
                    className="rounded-lg border border-green-500/30 bg-green-500/5 p-5"
                >
                    <div className="flex items-start gap-3">
                        <CheckCircle2 className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                        <div>
                            <h2 id="verified-heading" className="text-lg font-medium text-foreground">
                                {t("verifactu.verifiedTitle")}
                            </h2>
                            <p className="mt-1 text-sm text-muted-foreground">
                                {t("verifactu.verifiedDesc", {
                                    apoderado,
                                    date: status?.verified_at
                                        ? new Date(status.verified_at).toLocaleString("es-ES")
                                        : "-",
                                })}
                            </p>
                            <button
                                type="button"
                                onClick={handleReset}
                                disabled={busy}
                                className="mt-3 text-xs text-muted-foreground hover:text-foreground"
                            >
                                {t("verifactu.restartWizardMethod")}
                            </button>
                        </div>
                    </div>
                </section>
            )}

            {phase === "rejected" && (
                <section
                    aria-labelledby="rejected-heading"
                    role="alert"
                    className="rounded-lg border border-red-500/30 bg-red-500/5 p-5"
                >
                    <div className="flex items-start gap-3">
                        <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                        <div>
                            <h2 id="rejected-heading" className="text-lg font-medium text-foreground">
                                {t("verifactu.rejectedTitle")}
                            </h2>
                            <p className="mt-1 text-sm text-muted-foreground">
                                {status?.rejected_reason ?? t("verifactu.tryAgainLater")}
                            </p>
                            <button
                                type="button"
                                onClick={handleReset}
                                disabled={busy}
                                className="mt-3 px-3 py-1.5 rounded-md text-sm bg-background border border-border hover:border-primary"
                            >
                                {t("verifactu.retryWizard")}
                            </button>
                        </div>
                    </div>
                </section>
            )}
        </div>
    );
}

// ── Sub-componentes ─────────────────────────────────────────────────────────

const PHASES: { key: RegapStatus["status"] | "_done"; labelKey: string }[] = [
    { key: "not_started", labelKey: "verifactu.phaseIdentify" },
    { key: "identifying", labelKey: "verifactu.phaseGrant" },
    { key: "power_granted", labelKey: "verifactu.phaseVerify" },
    { key: "verified", labelKey: "verifactu.phaseDone" },
];

function PhaseStepper({ current }: { current: string }) {
    const t = useTranslations("configuracion");
    const order = ["not_started", "identifying", "cert_pending", "power_granted", "verified"];
    const currentIdx = order.indexOf(current);
    return (
        <nav aria-label={t("verifactu.wizardProgress")}>
            <ol className="flex items-center gap-2 text-xs">
                {PHASES.map((p, i) => {
                    const reached =
                        (p.key === "not_started" && currentIdx >= 0) ||
                        (p.key === "identifying" && currentIdx >= 1) ||
                        (p.key === "power_granted" && currentIdx >= 3) ||
                        (p.key === "verified" && currentIdx >= 4);
                    return (
                        <li key={p.key} className="flex items-center gap-2">
                            <span
                                className={`inline-flex items-center justify-center w-6 h-6 rounded-full border ${reached
                                    ? "bg-primary border-primary text-foreground"
                                    : "bg-background border-border text-muted-foreground"
                                    }`}
                            >
                                {i + 1}
                            </span>
                            <span className={reached ? "text-foreground" : "text-muted-foreground"}>
                                {t(p.labelKey)}
                            </span>
                            {i < PHASES.length - 1 && (
                                <span aria-hidden="true" className="w-6 h-px bg-border" />
                            )}
                        </li>
                    );
                })}
            </ol>
        </nav>
    );
}

interface BranchCardProps {
    icon: React.ReactNode;
    title: string;
    description: string;
    onClick: () => void;
    disabled: boolean;
}

function BranchCard({ icon, title, description, onClick, disabled }: BranchCardProps) {
    return (
        <button
            type="button"
            onClick={onClick}
            disabled={disabled}
            className="text-left p-4 rounded-lg border border-border bg-card hover:border-primary hover:bg-primary/5 disabled:opacity-50 transition-colors"
        >
            <div className="flex items-center gap-2 mb-2">
                {icon}
                <h3 className="text-sm font-semibold text-foreground">{title}</h3>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">{description}</p>
        </button>
    );
}

interface InstructionStep {
    text: string;
    detail?: string;
    href?: string;
    cta?: string;
}

function Instructions({ steps }: { steps: InstructionStep[] }) {
    return (
        <ol className="space-y-3">
            {steps.map((s, i) => (
                <li key={i} className="flex gap-3">
                    <span
                        aria-hidden="true"
                        className="flex-shrink-0 w-6 h-6 rounded-full bg-primary/15 text-primary flex items-center justify-center text-xs font-medium"
                    >
                        {i + 1}
                    </span>
                    <div className="flex-1 text-sm">
                        <p className="text-foreground leading-relaxed">{s.text}</p>
                        {s.detail && (
                            <p className="mt-1 text-xs font-mono text-muted-foreground bg-background border border-border rounded px-2 py-1 inline-block">
                                {s.detail}
                            </p>
                        )}
                        {s.href && s.cta && (
                            <a
                                href={s.href}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="mt-2 inline-flex items-center gap-1 text-primary text-xs hover:underline"
                            >
                                {s.cta} <ExternalLink className="w-3 h-3" />
                            </a>
                        )}
                    </div>
                </li>
            ))}
        </ol>
    );
}
