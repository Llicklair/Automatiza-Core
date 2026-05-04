"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
    AlertTriangle, CheckCircle2, FileKey2, Loader2, ShieldCheck, Trash2, Upload,
} from "lucide-react";
import { api } from "@/lib/api";
import type { CertificateStatus } from "@/lib/api";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { useToastStore } from "@/stores/toast";

const fmtDate = (d: string) =>
    new Date(d).toLocaleDateString("es-ES", { day: "2-digit", month: "long", year: "numeric" });

function isExpired(d: string) {
    return new Date(d) < new Date();
}

function isExpiringSoon(d: string) {
    const diff = new Date(d).getTime() - Date.now();
    return diff > 0 && diff < 30 * 24 * 60 * 60 * 1000;
}

export default function FirmaDigitalPage() {
    const toast = useToastStore();
    const fileRef = useRef<HTMLInputElement>(null);

    const [status, setStatus] = useState<CertificateStatus | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isUploading, setIsUploading] = useState(false);
    const [isDeleting, setIsDeleting] = useState(false);

    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [password, setPassword] = useState("");

    const load = useCallback(async () => {
        setIsLoading(true);
        try {
            setStatus(await api.tenant.certificate.status());
        } catch {
            toast.error("Error al cargar estado del certificado");
        } finally {
            setIsLoading(false);
        }
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => { load(); }, [load]);

    const handleUpload = async () => {
        if (!selectedFile) return;
        setIsUploading(true);
        try {
            const res = await api.tenant.certificate.upload(selectedFile, password);
            toast.success(res.message);
            setSelectedFile(null);
            setPassword("");
            if (fileRef.current) fileRef.current.value = "";
            await load();
        } catch (e: any) {
            toast.error(e?.message ?? "Error al subir certificado");
        } finally {
            setIsUploading(false);
        }
    };

    const handleDelete = async () => {
        if (!confirm("¿Eliminar el certificado? Las facturas se generarán sin firma.")) return;
        setIsDeleting(true);
        try {
            await api.tenant.certificate.delete();
            toast.success("Certificado eliminado");
            await load();
        } catch {
            toast.error("Error al eliminar certificado");
        } finally {
            setIsDeleting(false);
        }
    };

    return (
        <div className="p-6 space-y-6 max-w-2xl">
            <PageHeader
                title="Firma digital"
                description="Certificado PKCS#12 para firmar facturas FacturaE con XAdES-BES"
                icon={FileKey2}
            />

            {/* Current cert status */}
            <div className="rounded-xl border border-border bg-card p-5 space-y-4">
                <h2 className="text-sm font-semibold text-foreground">Certificado activo</h2>

                {isLoading ? (
                    <div className="flex items-center gap-2 text-muted-foreground text-sm">
                        <Loader2 className="w-4 h-4 animate-spin" /> Cargando…
                    </div>
                ) : !status?.has_certificate ? (
                    <div className="flex items-center gap-3 text-muted-foreground text-sm">
                        <ShieldCheck className="w-5 h-5 opacity-40" />
                        <span>No hay certificado configurado. Las facturas se exportarán sin firma.</span>
                    </div>
                ) : (
                    <div className="space-y-3">
                        <div className="flex items-start gap-3">
                            <CheckCircle2 className="w-5 h-5 text-emerald-400 mt-0.5 shrink-0" />
                            <div className="space-y-1">
                                <p className="text-sm font-medium text-foreground break-all">
                                    {status.cert_subject}
                                </p>
                                {status.cert_expires_at && (
                                    <p className={`text-xs flex items-center gap-1 ${
                                        isExpired(status.cert_expires_at)
                                            ? "text-red-400"
                                            : isExpiringSoon(status.cert_expires_at)
                                                ? "text-amber-400"
                                                : "text-muted-foreground"
                                    }`}>
                                        {isExpired(status.cert_expires_at) && (
                                            <AlertTriangle className="w-3 h-3" />
                                        )}
                                        Caduca el {fmtDate(status.cert_expires_at)}
                                        {isExpired(status.cert_expires_at) && " — CADUCADO"}
                                        {isExpiringSoon(status.cert_expires_at) && " — caduca pronto"}
                                    </p>
                                )}
                            </div>
                        </div>
                        <Button
                            variant="outline"
                            size="sm"
                            className="text-destructive border-destructive/30 hover:bg-destructive/10"
                            disabled={isDeleting}
                            onClick={handleDelete}
                        >
                            {isDeleting
                                ? <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
                                : <Trash2 className="mr-2 h-3.5 w-3.5" />}
                            Eliminar certificado
                        </Button>
                    </div>
                )}
            </div>

            {/* Upload new cert */}
            <div className="rounded-xl border border-border bg-card p-5 space-y-4">
                <h2 className="text-sm font-semibold text-foreground">
                    {status?.has_certificate ? "Reemplazar certificado" : "Cargar certificado"}
                </h2>
                <p className="text-xs text-muted-foreground">
                    Sube tu certificado de firma electrónica en formato <strong>.p12</strong> o <strong>.pfx</strong>.
                    Puede ser un certificado de persona física/jurídica emitido por la FNMT, Camerfirma, etc.
                </p>

                <div className="space-y-3">
                    <div>
                        <label className="text-xs text-muted-foreground block mb-1.5">Archivo (.p12 / .pfx)</label>
                        <input
                            ref={fileRef}
                            type="file"
                            accept=".p12,.pfx"
                            onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
                            className="block w-full text-sm text-muted-foreground
                                file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0
                                file:text-xs file:font-medium file:bg-primary file:text-primary-foreground
                                hover:file:bg-primary/90 cursor-pointer"
                        />
                    </div>

                    <div>
                        <label className="text-xs text-muted-foreground block mb-1.5">Contraseña del certificado</label>
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="Dejar vacío si no tiene contraseña"
                            className="w-full bg-muted border border-border rounded-lg px-3 py-2 text-sm
                                text-foreground placeholder:text-muted-foreground/50
                                focus:outline-none focus:border-primary/50"
                        />
                    </div>

                    <Button
                        onClick={handleUpload}
                        disabled={!selectedFile || isUploading}
                    >
                        {isUploading
                            ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Validando y guardando…</>
                            : <><Upload className="mr-2 h-4 w-4" />Cargar certificado</>}
                    </Button>
                </div>
            </div>

            <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 px-4 py-3 text-xs text-amber-400 space-y-1">
                <p className="font-medium flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5" /> Nota de seguridad
                </p>
                <p>
                    La contraseña del certificado se almacena en la base de datos.
                    Para entornos de producción con alta seguridad, considera usar un HSM o un vault externo.
                </p>
            </div>
        </div>
    );
}
