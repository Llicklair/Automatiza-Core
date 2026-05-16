/**
 * UI.ONB — wizard onboarding focado de 4 pasos.
 *
 *   1. company  — alta empresa (deep-link Configuración → Empresa)
 *   2. cert     — apoderamiento AEAT (deep-link /configuracion/regap)
 *   3. data     — conectar N43 / importar Holded / CSV
 *   4. use_case — caso de uso guiado (primera factura, primera nómina...)
 *
 * + Skip-to-end (marca el wizard como `skipped_at`)
 * + Vídeo embebido 90s (placeholder hasta que el fundador grabe el real)
 *
 * Diferente al checklist largo de `/primeros-pasos` — este wizard es la
 * primera experiencia del usuario tras signup y prioriza arrancar rápido.
 */
"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
    ArrowRight,
    CheckCircle2,
    Circle,
    ExternalLink,
    FastForward,
    Loader2,
    Play,
    PlayCircle,
    RefreshCw,
    Sparkles,
} from "lucide-react";
import { api } from "@/lib/api";
import type { OnboardingState, OnboardingStepKey } from "@/lib/api/onboarding";
import { useToastStore } from "@/stores/toast";

interface StepDef {
    key: OnboardingStepKey;
    title: string;
    description: string;
    cta: string;
    href: string;
    estimateMin: number;
}

const STEPS: StepDef[] = [
    {
        key: "company",
        title: "Configura tu empresa",
        description:
            "Añade nombre, NIF y dirección fiscal. Estos datos aparecerán en todas tus facturas y modelos AEAT.",
        cta: "Ir a Configuración → Empresa",
        href: "/configuracion/empresa",
        estimateMin: 2,
    },
    {
        key: "cert",
        title: "Apodera a AutomatizaPyme en AEAT (REGAP)",
        description:
            "Para que el agente presente declaraciones telemáticas en tu nombre, otorga apoderamiento en Sede Electrónica. Tres opciones: Cl@ve PIN, Cl@ve Permanente o cert FNMT.",
        cta: "Abrir wizard REGAP",
        href: "/configuracion/regap",
        estimateMin: 10,
    },
    {
        key: "data",
        title: "Trae tus datos existentes",
        description:
            "Importa tus clientes/facturas desde Holded o CSV, o conecta el N43 de tu banco para reconciliación automática. Si empiezas desde cero, puedes saltar este paso.",
        cta: "Ir a Importar / Integraciones",
        href: "/configuracion/integraciones",
        estimateMin: 5,
    },
    {
        key: "use_case",
        title: "Haz tu primera acción guiada",
        description:
            "Crea tu primera factura — el agente te guía paso a paso. En 60 segundos verás el sistema funcionando end-to-end con datos reales tuyos.",
        cta: "Crear primera factura",
        href: "/ventas/facturas",
        estimateMin: 3,
    },
];

export default function BienvenidaPage() {
    const router = useRouter();
    const toast = useToastStore();
    const [state, setState] = useState<OnboardingState | null>(null);
    const [loading, setLoading] = useState(true);
    const [busy, setBusy] = useState<string | null>(null);

    const load = useCallback(async () => {
        setLoading(true);
        try {
            const res = await api.onboarding.get();
            setState(res);
        } catch (e: any) {
            toast.show(`Error: ${e.message}`, "error");
        } finally {
            setLoading(false);
        }
    }, [toast]);

    useEffect(() => {
        load();
    }, [load]);

    async function toggleStep(step: OnboardingStepKey, value: boolean) {
        setBusy(step);
        try {
            const next = await api.onboarding.setStep(step, value);
            setState(next);
            if (next.completed_at) {
                toast.show("¡Onboarding completado! 🎉", "success");
            }
        } catch (e: any) {
            toast.show(`Error: ${e.message}`, "error");
        } finally {
            setBusy(null);
        }
    }

    async function handleSkip() {
        setBusy("__skip__");
        try {
            await api.onboarding.skip();
            toast.show("Wizard saltado. Puedes retomarlo desde Primeros Pasos.", "info");
            router.push("/");
        } catch (e: any) {
            toast.show(`Error: ${e.message}`, "error");
        } finally {
            setBusy(null);
        }
    }

    async function handleReset() {
        setBusy("__reset__");
        try {
            const next = await api.onboarding.reset();
            setState(next);
        } catch (e: any) {
            toast.show(`Error: ${e.message}`, "error");
        } finally {
            setBusy(null);
        }
    }

    if (loading || !state) {
        return (
            <div className="p-8 flex items-center gap-3 text-muted-foreground">
                <Loader2 className="w-4 h-4 animate-spin" /> Cargando…
            </div>
        );
    }

    const completedCount = STEPS.filter(
        (s) => state[`step_${s.key}` as keyof OnboardingState] === true,
    ).length;
    const pct = Math.round((completedCount / STEPS.length) * 100);
    const totalMinutes = STEPS.reduce((acc, s) => acc + s.estimateMin, 0);

    return (
        <div className="p-6 max-w-3xl mx-auto space-y-6">
            <header>
                <div className="flex items-center gap-3 mb-2">
                    <Sparkles className="w-5 h-5 text-primary" aria-hidden="true" />
                    <h1 className="text-2xl font-semibold text-foreground tracking-tight">
                        Bienvenido a AutomatizaPyme
                    </h1>
                </div>
                <p className="text-sm text-muted-foreground">
                    Cuatro pasos rápidos para tener tu ERP operativo. Tiempo estimado total:
                    <strong> {totalMinutes} minutos</strong>. Puedes saltar cualquiera y volver luego.
                </p>
            </header>

            {/* Vídeo embebido (placeholder hasta grabación oficial) */}
            <div
                role="region"
                aria-label="Vídeo tutorial 90 segundos"
                className="rounded-lg border border-border bg-card overflow-hidden"
            >
                <div className="aspect-video bg-muted flex items-center justify-center relative">
                    <div className="flex flex-col items-center gap-2 text-muted-foreground">
                        <PlayCircle className="w-12 h-12" aria-hidden="true" />
                        <p className="text-xs">Vídeo tutorial · 90 segundos</p>
                        <p className="text-[10px] italic">(se incrustará tras grabación oficial)</p>
                    </div>
                </div>
            </div>

            {/* Progress bar */}
            <div className="rounded-lg border border-border bg-card p-4">
                <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-foreground">
                        {completedCount === STEPS.length
                            ? "Onboarding completado 🎉"
                            : `${completedCount} de ${STEPS.length} pasos`}
                    </span>
                    <span className="text-sm font-semibold text-primary">{pct}%</span>
                </div>
                <div
                    role="progressbar"
                    aria-valuenow={pct}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    aria-label="Progreso del onboarding"
                    className="w-full bg-muted rounded-full h-2 overflow-hidden"
                >
                    <div
                        className="h-full bg-gradient-to-r from-indigo-600 to-violet-500 rounded-full transition-all duration-500"
                        style={{ width: `${pct}%` }}
                    />
                </div>
            </div>

            {/* Steps */}
            <ol className="space-y-3">
                {STEPS.map((step, idx) => {
                    const done = state[`step_${step.key}` as keyof OnboardingState] === true;
                    const isBusy = busy === step.key;
                    return (
                        <li
                            key={step.key}
                            className={`rounded-lg border p-4 transition-colors ${done
                                ? "border-emerald-500/30 bg-emerald-500/5"
                                : "border-border bg-card hover:border-primary"
                                }`}
                        >
                            <div className="flex items-start gap-3">
                                <button
                                    type="button"
                                    onClick={() => toggleStep(step.key, !done)}
                                    disabled={isBusy}
                                    aria-label={
                                        done
                                            ? `Marcar "${step.title}" como pendiente`
                                            : `Marcar "${step.title}" como completado`
                                    }
                                    aria-pressed={done}
                                    className="flex-shrink-0 mt-0.5"
                                >
                                    {done ? (
                                        <CheckCircle2 className="w-6 h-6 text-emerald-500" />
                                    ) : (
                                        <Circle className="w-6 h-6 text-muted-foreground hover:text-primary transition-colors" />
                                    )}
                                </button>
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center justify-between gap-2">
                                        <h2
                                            className={`text-sm font-semibold ${done ? "text-foreground line-through opacity-70" : "text-foreground"
                                                }`}
                                        >
                                            {idx + 1}. {step.title}
                                        </h2>
                                        <span className="text-[10px] uppercase tracking-wider text-muted-foreground flex-shrink-0">
                                            ~{step.estimateMin} min
                                        </span>
                                    </div>
                                    <p className="mt-1 text-xs text-muted-foreground leading-relaxed">
                                        {step.description}
                                    </p>
                                    <div className="mt-3 flex items-center gap-3">
                                        <Link
                                            href={step.href}
                                            className="inline-flex items-center gap-1.5 text-xs text-primary hover:underline"
                                        >
                                            <Play className="w-3 h-3" aria-hidden="true" />
                                            {step.cta}
                                            <ArrowRight className="w-3 h-3" aria-hidden="true" />
                                        </Link>
                                        {isBusy && (
                                            <Loader2
                                                className="w-3 h-3 animate-spin text-muted-foreground"
                                                aria-hidden="true"
                                            />
                                        )}
                                    </div>
                                </div>
                            </div>
                        </li>
                    );
                })}
            </ol>

            {/* Footer actions */}
            <div className="flex items-center justify-between pt-4 border-t border-border">
                <button
                    type="button"
                    onClick={handleSkip}
                    disabled={!!busy}
                    className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
                >
                    <FastForward className="w-3.5 h-3.5" aria-hidden="true" />
                    Saltar el wizard (puedo continuar luego)
                </button>
                {state.completed_at && (
                    <button
                        type="button"
                        onClick={handleReset}
                        disabled={!!busy}
                        className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground"
                    >
                        <RefreshCw className="w-3 h-3" aria-hidden="true" /> Reiniciar wizard
                    </button>
                )}
            </div>

            {/* UI.SIM — preview del Modelo 303 con datos ejemplo */}
            <aside className="rounded-lg border border-primary/30 bg-primary/5 p-4">
                <h2 className="text-sm font-semibold text-foreground mb-1">
                    ¿Quieres ver el sistema funcionando antes de meter tus datos?
                </h2>
                <p className="text-xs text-muted-foreground mb-2">
                    Hemos preparado un Modelo 303 calculado sobre un autónomo prototípico para que veas exactamente qué genera AutomatizaPyme.
                </p>
                <Link
                    href="/bienvenida/simulacion-303"
                    className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline"
                >
                    Ver simulación Modelo 303 <ArrowRight className="w-3 h-3" aria-hidden="true" />
                </Link>
            </aside>

            {/* Enlace al checklist largo */}
            <aside className="text-center text-xs text-muted-foreground">
                ¿Buscas el checklist completo de funcionalidades?{" "}
                <Link href="/primeros-pasos" className="text-primary hover:underline inline-flex items-center gap-1">
                    Ver Primeros Pasos <ExternalLink className="w-3 h-3" aria-hidden="true" />
                </Link>
            </aside>
        </div>
    );
}
