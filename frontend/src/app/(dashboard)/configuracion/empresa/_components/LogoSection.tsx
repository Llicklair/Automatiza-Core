"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { CheckCircle2, ImageIcon, Loader2, Trash2, Upload } from "lucide-react";

import { api } from "@/lib/api";
import type { LogoStatus } from "@/lib/api/tenant";
import { Button } from "@/components/ui/button";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";

const ALLOWED = ["image/png", "image/jpeg", "image/gif", "image/webp"];
const MAX_BYTES = 2 * 1024 * 1024; // 2 MB — sincronizado con el backend

export function LogoSection() {
    const toast = useToastStore();
    const fileRef = useRef<HTMLInputElement>(null);

    const [status, setStatus] = useState<LogoStatus | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isUploading, setIsUploading] = useState(false);
    const [isDeleting, setIsDeleting] = useState(false);

    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [previewUrl, setPreviewUrl] = useState<string | null>(null);

    const load = useCallback(async () => {
        setIsLoading(true);
        try {
            setStatus(await api.tenant.logo.status());
        } catch {
            toast.error("Error al cargar estado del logo");
        } finally {
            setIsLoading(false);
        }
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => {
        load();
    }, [load]);

    useEffect(() => {
        if (!selectedFile) {
            setPreviewUrl(null);
            return;
        }
        const url = URL.createObjectURL(selectedFile);
        setPreviewUrl(url);
        return () => URL.revokeObjectURL(url);
    }, [selectedFile]);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0] ?? null;
        if (!file) {
            setSelectedFile(null);
            return;
        }
        if (!ALLOWED.includes(file.type)) {
            toast.error("Formato no soportado. Usa PNG, JPG, GIF o WebP.");
            if (fileRef.current) fileRef.current.value = "";
            return;
        }
        if (file.size > MAX_BYTES) {
            toast.error("El logo no puede superar 2 MB.");
            if (fileRef.current) fileRef.current.value = "";
            return;
        }
        setSelectedFile(file);
    };

    const handleUpload = async () => {
        if (!selectedFile) return;
        setIsUploading(true);
        try {
            const res = await api.tenant.logo.upload(selectedFile);
            toast.success(res.message);
            setSelectedFile(null);
            if (fileRef.current) fileRef.current.value = "";
            await load();
        } catch (e: any) {
            toast.error(e?.message ?? "Error al subir el logo");
        } finally {
            setIsUploading(false);
        }
    };

    const handleDelete = async () => {
        if (!(await showConfirm({
            message: "¿Eliminar el logo? Los próximos informes se generarán sin él.",
            confirmLabel: "Eliminar",
            confirmVariant: "danger",
        }))) return;
        setIsDeleting(true);
        try {
            await api.tenant.logo.delete();
            toast.success("Logo eliminado");
            await load();
        } catch {
            toast.error("Error al eliminar el logo");
        } finally {
            setIsDeleting(false);
        }
    };

    const hasLogo = !!status?.has_logo;

    return (
        <div className="bg-card border border-border rounded-2xl p-6 space-y-5">
            <div>
                <h2 className="text-lg font-semibold text-foreground flex items-center gap-2">
                    <ImageIcon className="w-4 h-4 text-primary" />
                    Logo de la empresa
                </h2>
                <p className="text-xs text-muted-foreground mt-1">
                    Aparecerá en la portada y el pie de los informes PDF generados por los agentes IA.
                    Recomendado: PNG con fondo transparente, ~500 px de ancho. Máximo 2 MB.
                </p>
            </div>

            {/* Estado actual */}
            {isLoading ? (
                <div className="flex items-center gap-2 text-muted-foreground text-sm">
                    <Loader2 className="w-4 h-4 animate-spin" /> Cargando…
                </div>
            ) : !hasLogo && !selectedFile ? (
                <div className="rounded-xl border border-dashed border-border bg-muted/30 px-4 py-6 text-center text-sm text-muted-foreground">
                    No hay logo configurado.
                </div>
            ) : (
                <div className="rounded-xl border border-border bg-muted/30 p-4 flex items-center gap-4">
                    <div className="w-32 h-20 bg-background border border-border rounded-lg flex items-center justify-center overflow-hidden">
                        {previewUrl ? (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img src={previewUrl} alt="Vista previa del nuevo logo" className="max-w-full max-h-full object-contain" />
                        ) : (
                            <div className="text-emerald-400 flex flex-col items-center gap-1">
                                <CheckCircle2 className="w-6 h-6" />
                                <span className="text-[10px] uppercase tracking-wider">Configurado</span>
                            </div>
                        )}
                    </div>
                    <div className="flex-1 text-sm">
                        {selectedFile ? (
                            <>
                                <p className="text-foreground font-medium break-all">{selectedFile.name}</p>
                                <p className="text-xs text-muted-foreground mt-0.5">
                                    {(selectedFile.size / 1024).toFixed(1)} KB · sin guardar
                                </p>
                            </>
                        ) : (
                            <>
                                <p className="text-foreground font-medium">Logo activo</p>
                                <p className="text-xs text-muted-foreground mt-0.5">
                                    La vista previa se ve cuando un agente genera un informe.
                                </p>
                            </>
                        )}
                    </div>
                    {hasLogo && !selectedFile && (
                        <Button
                            variant="outline"
                            size="sm"
                            className="text-destructive border-destructive/30 hover:bg-destructive/10"
                            disabled={isDeleting}
                            onClick={handleDelete}
                        >
                            {isDeleting ? <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" /> : <Trash2 className="mr-2 h-3.5 w-3.5" />}
                            Eliminar
                        </Button>
                    )}
                </div>
            )}

            {/* Selector + upload */}
            <div className="space-y-3 pt-2 border-t border-border">
                <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider block">
                    {hasLogo ? "Reemplazar logo" : "Subir logo"}
                </label>
                <input
                    ref={fileRef}
                    type="file"
                    accept="image/png,image/jpeg,image/gif,image/webp"
                    onChange={handleFileChange}
                    className="block w-full text-sm text-muted-foreground
                        file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0
                        file:text-xs file:font-medium file:bg-primary file:text-primary-foreground
                        hover:file:bg-primary/90 cursor-pointer"
                />
                {selectedFile && (
                    <Button onClick={handleUpload} disabled={isUploading}>
                        {isUploading ? (
                            <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Subiendo…
                            </>
                        ) : (
                            <>
                                <Upload className="mr-2 h-4 w-4" />
                                Guardar logo
                            </>
                        )}
                    </Button>
                )}
            </div>
        </div>
    );
}
