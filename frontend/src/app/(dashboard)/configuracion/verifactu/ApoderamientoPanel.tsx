/**
 * PRES.REG — wizard onboarding REGAP (apoderamiento AEAT).
 *
 * Tres ramas (Cl@ve PIN / Cl@ve Permanente / Cert FNMT) más verificación
 * final contra REGAP. La consulta REGAP está mocked hasta DEC.14 (alta
 * colaborador social) — la UI ya está completa para que cuando el endpoint
 * real esté disponible sea solo flip de feature flag en el backend.
 */
"use client";

import { useCallback, useEffect, useState } from "react";
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
            toast.show(`Error cargando estado REGAP: ${e.message}`, "error");
        } finally {
            setLoading(false);
        }
    }, [toast]);

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
            toast.show(`Error: ${e.message}`, "error");
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
            toast.show(`Error: ${e.message}`, "error");
        } finally {
            setBusy(false);
        }
    }

    async function handleVerify() {
        if (!nifCliente.trim()) {
            toast.show("Introduce el NIF del cliente apoderado", "warning");
            return;
        }
        setBusy(true);
        try {
            const updated = await api.regap.verify(nifCliente.trim().toUpperCase());
            setStatus(updated);
            if (updated.status === "verified") {
                toast.show("Apoderamiento verificado ✓", "success");
            } else if (updated.status === "rejected") {
                toast.show("La consulta REGAP no encontró un apoderamiento vigente", "error");
            }
        } catch (e: any) {
            toast.show(`Error: ${e.message}`, "error");
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
            toast.show(`Error: ${e.message}`, "error");
        } finally {
            setBusy(false);
        }
    }

    if (loading) {
        return (
            <div className="p-8 flex items-center gap-3 text-muted-foreground">
                <Loader2 className="w-4 h-4 animate-spin" /> Cargando estado REGAP…
            </div>
        );
    }

    const phase = status?.status ?? "not_started";
    const apoderado = status?.apoderado_nombre ?? "AutomatizaPyme S.L.";

    return (
        <div className="space-y-6">
            <header>
                <h1 className="text-2xl font-semibold text-foreground tracking-tight">
                    Apoderamiento AEAT (REGAP)
                </h1>
                <p className="mt-1 text-sm text-muted-foreground">
                    Para que <strong>{apoderado}</strong> pueda presentar tus declaraciones telemáticas
                    en tu nombre, necesitas otorgarnos apoderamiento en la Sede Electrónica de la AEAT.
                    Es gratuito y queda registrado en REGAP. El trámite se hace una sola vez.
                </p>
            </header>

            <PhaseStepper current={phase} />

            {phase === "not_started" && (
                <section aria-labelledby="branch-heading" className="space-y-4">
                    <h2 id="branch-heading" className="text-lg font-medium text-foreground">
                        ¿Cómo te identificas hoy en la Sede Electrónica de la AEAT?
                    </h2>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        <BranchCard
                            icon={<KeyRound className="w-5 h-5 text-primary" />}
                            title="Ya tengo Cl@ve"
                            description="Tengo Cl@ve PIN o Cl@ve Permanente activos."
                            onClick={() => handleStartBranch("tiene_clave")}
                            disabled={busy}
                        />
                        <BranchCard
                            icon={<KeyRound className="w-5 h-5 text-primary" />}
                            title="Quiero obtener Cl@ve"
                            description="Aún no tengo. Es el método más rápido (10 min)."
                            onClick={() => handleStartBranch("quiere_clave")}
                            disabled={busy}
                        />
                        <BranchCard
                            icon={<ShieldCheck className="w-5 h-5 text-primary" />}
                            title="Quiero certificado FNMT"
                            description="Prefiero certificado digital. Tarda 5-10 días."
                            onClick={() => handleStartBranch("quiere_cert_fnmt")}
                            disabled={busy}
                        />
                    </div>
                </section>
            )}

            {(phase === "identifying" || phase === "cert_pending") && (
                <section aria-labelledby="instruct-heading" className="space-y-4">
                    <h2 id="instruct-heading" className="text-lg font-medium text-foreground">
                        Paso 2 · Otorga el apoderamiento en Sede AEAT
                    </h2>

                    {status?.auth_method === "cert_fnmt" && (
                        <Instructions
                            steps={[
                                {
                                    text: "Solicita tu certificado FNMT en persona-física (online). Tarda 5-10 días en estar listo.",
                                    href: URL_FNMT_PERSONA_FISICA,
                                    cta: "Solicitar certificado FNMT",
                                },
                                {
                                    text: "Cuando tengas el certificado instalado en tu navegador, accede a Apoderamientos AEAT y otorga representación a:",
                                    detail: `NIF apoderado: ${status.apoderado_nif} — ${apoderado}`,
                                    href: URL_REGAP_OTORGAR,
                                    cta: "Otorgar apoderamiento (REGAP)",
                                },
                                {
                                    text: "Marca trámite: PRESENTACION_DECLARACIONES. Vigencia: 5 años renovable.",
                                },
                            ]}
                        />
                    )}

                    {status?.auth_method === "clave_pin" && (
                        <Instructions
                            steps={[
                                {
                                    text: "Regístrate en Cl@ve (en línea o presencialmente en oficinas autorizadas).",
                                    href: URL_CLAVE_REGISTRO,
                                    cta: "Registrarse en Cl@ve",
                                },
                                {
                                    text: "Una vez registrado, accede a Apoderamientos AEAT con Cl@ve y otorga representación a:",
                                    detail: `NIF apoderado: ${status.apoderado_nif} — ${apoderado}`,
                                    href: URL_REGAP_OTORGAR,
                                    cta: "Otorgar apoderamiento (REGAP)",
                                },
                                {
                                    text: "Marca trámite: PRESENTACION_DECLARACIONES.",
                                },
                            ]}
                        />
                    )}

                    {status?.auth_method === "clave_permanente" && (
                        <Instructions
                            steps={[
                                {
                                    text: "Accede directamente a la Sede AEAT con Cl@ve Permanente.",
                                    href: URL_CLAVE_AEAT,
                                    cta: "Abrir Sede AEAT",
                                },
                                {
                                    text: "Entra al menú Apoderamientos y otorga representación a:",
                                    detail: `NIF apoderado: ${status?.apoderado_nif} — ${apoderado}`,
                                    href: URL_REGAP_OTORGAR,
                                    cta: "Otorgar apoderamiento (REGAP)",
                                },
                                {
                                    text: "Marca trámite: PRESENTACION_DECLARACIONES.",
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
                            He completado el apoderamiento en Sede AEAT
                        </button>
                        <button
                            type="button"
                            onClick={handleReset}
                            disabled={busy}
                            className="px-3 py-2 rounded-md text-sm text-muted-foreground hover:text-foreground flex items-center gap-1.5"
                        >
                            <RefreshCw className="w-3.5 h-3.5" /> Cambiar método
                        </button>
                    </div>
                </section>
            )}

            {phase === "power_granted" && (
                <section aria-labelledby="verify-heading" className="space-y-4">
                    <h2 id="verify-heading" className="text-lg font-medium text-foreground">
                        Paso 3 · Verifica el apoderamiento contra REGAP
                    </h2>
                    <p className="text-sm text-muted-foreground">
                        Vamos a comprobar que el apoderamiento está vigente en el registro REGAP de la AEAT.
                        Esta consulta es de solo lectura y no modifica ningún dato.
                    </p>
                    <div>
                        <label htmlFor="nif-cliente" className="block text-sm font-medium text-foreground mb-1.5">
                            NIF del cliente apoderado
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
                            Consultar REGAP
                        </button>
                        <button
                            type="button"
                            onClick={handleReset}
                            disabled={busy}
                            className="px-3 py-2 rounded-md text-sm text-muted-foreground hover:text-foreground"
                        >
                            Reiniciar wizard
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
                                Apoderamiento verificado
                            </h2>
                            <p className="mt-1 text-sm text-muted-foreground">
                                {apoderado} ya puede presentar declaraciones en tu nombre. El apoderamiento
                                fue confirmado el{" "}
                                {status?.verified_at
                                    ? new Date(status.verified_at).toLocaleString("es-ES")
                                    : "-"}
                                .
                            </p>
                            <button
                                type="button"
                                onClick={handleReset}
                                disabled={busy}
                                className="mt-3 text-xs text-muted-foreground hover:text-foreground"
                            >
                                Iniciar wizard de nuevo (cambio de método)
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
                                Apoderamiento no encontrado en REGAP
                            </h2>
                            <p className="mt-1 text-sm text-muted-foreground">
                                {status?.rejected_reason ?? "Inténtalo de nuevo más tarde."}
                            </p>
                            <button
                                type="button"
                                onClick={handleReset}
                                disabled={busy}
                                className="mt-3 px-3 py-1.5 rounded-md text-sm bg-background border border-border hover:border-primary"
                            >
                                Reintentar wizard
                            </button>
                        </div>
                    </div>
                </section>
            )}
        </div>
    );
}

// ── Sub-componentes ─────────────────────────────────────────────────────────

const PHASES: { key: RegapStatus["status"] | "_done"; label: string }[] = [
    { key: "not_started", label: "Identificación" },
    { key: "identifying", label: "Apoderar" },
    { key: "power_granted", label: "Verificar" },
    { key: "verified", label: "Listo" },
];

function PhaseStepper({ current }: { current: string }) {
    const order = ["not_started", "identifying", "cert_pending", "power_granted", "verified"];
    const currentIdx = order.indexOf(current);
    return (
        <nav aria-label="Progreso del wizard">
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
                                {p.label}
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
