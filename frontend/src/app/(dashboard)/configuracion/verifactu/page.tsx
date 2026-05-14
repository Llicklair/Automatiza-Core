/**
 * FAC.MODE — Settings del modo de remisión Verifactu.
 *
 * Dos modos según RD 1007/2023:
 *   - voluntary    — VERI*FACTU: cada factura se envía a AEAT al emitirse
 *   - no_remission — SIF puro: cadena hash local, sin envío automático
 *
 * Hasta DEC.14 (alta colaborador social) y PRES.0 (cert representación)
 * completados, voluntary no funciona en producción — la UI lo señala.
 */
"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Info, Loader2, ShieldAlert } from "lucide-react";
import { api } from "@/lib/api";
import type { VerifactuConfig, VerifactuMode } from "@/lib/api/verifactuConfig";
import { useToastStore } from "@/stores/toast";

export default function VerifactuConfigPage() {
    const [data, setData] = useState<VerifactuConfig | null>(null);
    const [loading, setLoading] = useState(true);
    const [busy, setBusy] = useState(false);
    const toast = useToastStore();

    async function load() {
        setLoading(true);
        try {
            const res = await api.verifactuConfig.get();
            setData(res);
        } catch (e: any) {
            toast.show(`Error: ${e.message}`, "error");
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        load();
    }, []);

    async function setMode(mode: VerifactuMode) {
        setBusy(true);
        try {
            const res = await api.verifactuConfig.set(mode);
            setData(res);
            toast.show(
                mode === "voluntary"
                    ? "Modo VERI*FACTU activado"
                    : "Modo sin remisión activado",
                "success",
            );
        } catch (e: any) {
            toast.show(`Error: ${e.message}`, "error");
        } finally {
            setBusy(false);
        }
    }

    if (loading || !data) {
        return (
            <div className="p-8 flex items-center gap-3 text-muted-foreground">
                <Loader2 className="w-4 h-4 animate-spin" /> Cargando…
            </div>
        );
    }

    return (
        <div className="p-6 max-w-3xl space-y-6">
            <header>
                <h1 className="text-2xl font-semibold text-foreground tracking-tight">
                    Modo Verifactu
                </h1>
                <p className="mt-1 text-sm text-muted-foreground">
                    Según el RD 1007/2023, el sistema puede operar en dos modos. Elige el
                    que aplica a tu negocio. Puedes cambiarlo cuando quieras.
                </p>
            </header>

            <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-4 flex items-start gap-3">
                <ShieldAlert
                    className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5"
                    aria-hidden="true"
                />
                <p className="text-xs text-muted-foreground leading-relaxed">
                    El modo <strong>VERI*FACTU</strong> requiere el alta como colaborador social
                    en AEAT y el certificado de representación. Hasta tenerlos, la activación
                    se queda en preparación local — las facturas se firman con hash pero la
                    remisión efectiva está pendiente del setup administrativo.
                </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <ModeCard
                    selected={data.mode === "no_remission"}
                    label="Sin remisión (SIF)"
                    description="El sistema genera la cadena hash y la conserva en local. La AEAT puede requerir la información a posteriori. Es la opción por defecto y la más segura mientras el alta administrativa esté en curso."
                    bullets={[
                        "Sin envío automático a AEAT",
                        "Cadena `huella` íntegra y verificable",
                        "Cumple RD 1007/2023 art. 6 (SIF)",
                    ]}
                    onSelect={() => setMode("no_remission")}
                    busy={busy}
                />
                <ModeCard
                    selected={data.mode === "voluntary"}
                    label="VERI*FACTU"
                    description="Cada factura se remite telemáticamente a la AEAT al emitirse con firma XAdES y acuse de recibo. Es la modalidad voluntaria que da máxima transparencia frente a inspección."
                    bullets={[
                        "Remisión inmediata a AEAT",
                        "Acuse de recibo archivado por factura",
                        "Recomendado tras DEC.14 + DEC.15",
                    ]}
                    onSelect={() => setMode("voluntary")}
                    busy={busy}
                    highlight
                />
            </div>

            <p className="text-xs text-muted-foreground">
                Último cambio: {new Date(data.updated_at).toLocaleString("es-ES")}
                {data.is_default && " · valor por defecto"}
            </p>
        </div>
    );
}

function ModeCard({
    selected,
    label,
    description,
    bullets,
    onSelect,
    busy,
    highlight,
}: {
    selected: boolean;
    label: string;
    description: string;
    bullets: string[];
    onSelect: () => void;
    busy: boolean;
    highlight?: boolean;
}) {
    return (
        <article
            className={`rounded-lg border p-5 transition-colors ${selected
                ? "border-primary bg-primary/5 ring-1 ring-primary/30"
                : "border-border bg-card hover:border-primary/50"
                }`}
        >
            <div className="flex items-center justify-between mb-1.5">
                <h2 className="text-sm font-semibold text-foreground">{label}</h2>
                {selected && (
                    <CheckCircle2
                        className="w-4 h-4 text-primary"
                        aria-label="Modo activo"
                    />
                )}
                {highlight && !selected && (
                    <span
                        className="text-[10px] uppercase tracking-wider text-primary border border-primary/30 rounded px-1.5 py-0.5"
                        aria-hidden="true"
                    >
                        recomendado
                    </span>
                )}
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed mb-3">
                {description}
            </p>
            <ul className="space-y-1 mb-4">
                {bullets.map((b) => (
                    <li
                        key={b}
                        className="flex items-start gap-2 text-xs text-foreground"
                    >
                        <Info
                            className="w-3 h-3 text-primary flex-shrink-0 mt-0.5"
                            aria-hidden="true"
                        />
                        {b}
                    </li>
                ))}
            </ul>
            <button
                type="button"
                onClick={onSelect}
                disabled={busy || selected}
                aria-pressed={selected}
                className={`w-full px-3 py-2 rounded-md text-sm font-medium transition-colors disabled:cursor-default ${selected
                    ? "bg-primary/15 text-primary"
                    : "bg-primary text-foreground hover:bg-primary/90"
                    }`}
            >
                {selected ? "Activo" : "Activar este modo"}
            </button>
        </article>
    );
}
