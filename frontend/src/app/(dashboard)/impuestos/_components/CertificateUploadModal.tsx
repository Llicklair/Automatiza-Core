"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { X, Loader2, ShieldCheck, AlertTriangle, KeyRound, Upload } from "lucide-react";
import { api } from "@/lib/api";
import { useToastStore } from "@/stores/toast";

interface Props {
    open: boolean;
    onClose: () => void;
    onUploaded: () => void;
}

export function CertificateUploadModal({ open, onClose, onUploaded }: Props) {
    const t = useTranslations("impuestos");
    const tc = useTranslations("common");
    const toast = useToastStore();
    const [file, setFile] = useState<File | null>(null);
    const [password, setPassword] = useState("");
    const [label, setLabel] = useState(t("certificado.labelDefault"));
    const [notes, setNotes] = useState("");
    const [busy, setBusy] = useState(false);

    if (!open) return null;

    const reset = () => {
        setFile(null); setPassword(""); setLabel(t("certificado.labelDefault")); setNotes("");
    };
    const handleClose = () => { reset(); onClose(); };

    const handleSubmit = async () => {
        if (!file) { toast.error(t("certificado.selectFileError")); return; }
        if (!password) { toast.error(t("certificado.passwordRequired")); return; }
        setBusy(true);
        try {
            await api.aeat.certificate.upload(file, password, label, notes || undefined);
            toast.success(t("certificado.saved"));
            reset();
            onUploaded();
            onClose();
        } catch (e) {
            toast.error(e instanceof Error ? e.message : t("certificado.uploadError"));
        } finally {
            setBusy(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={handleClose}>
            <div
                className="bg-background border border-border rounded-xl w-full max-w-md max-h-[90vh] overflow-auto p-6"
                onClick={(e) => e.stopPropagation()}
            >
                <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3">
                        <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-primary/15 text-primary flex items-center justify-center">
                            <ShieldCheck className="w-5 h-5" />
                        </div>
                        <div>
                            <h3 className="text-base font-semibold text-foreground">{t("certificado.title")}</h3>
                            <p className="text-xs text-muted-foreground mt-0.5">
                                {t("certificado.subtitle")}
                            </p>
                        </div>
                    </div>
                    <button onClick={handleClose} className="text-muted-foreground hover:text-foreground" aria-label={t("certificado.closeAria")}>
                        <X className="w-4 h-4" />
                    </button>
                </div>

                <div className="mt-5 space-y-3">
                    <div>
                        <label className="block text-xs font-medium text-muted-foreground mb-1">{t("certificado.ficheroLabel")}</label>
                        <label className="flex items-center gap-2 h-10 px-3 rounded-md border border-dashed border-border bg-card hover:bg-muted/30 cursor-pointer transition-colors">
                            <Upload className="w-4 h-4 text-muted-foreground" />
                            <span className="text-sm text-foreground truncate">{file ? file.name : t("certificado.selectFile")}</span>
                            <input
                                type="file"
                                accept=".pfx,.p12,application/x-pkcs12"
                                className="hidden"
                                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                            />
                        </label>
                    </div>

                    <div>
                        <label className="block text-xs font-medium text-muted-foreground mb-1">{t("certificado.passwordLabel")}</label>
                        <div className="flex items-center gap-2 h-10 px-3 rounded-md border border-border bg-card">
                            <KeyRound className="w-4 h-4 text-muted-foreground" />
                            <input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="••••••••"
                                className="flex-1 bg-transparent border-0 outline-none text-sm"
                            />
                        </div>
                    </div>

                    <div>
                        <label className="block text-xs font-medium text-muted-foreground mb-1">{t("certificado.etiquetaLabel")}</label>
                        <input
                            value={label}
                            onChange={(e) => setLabel(e.target.value)}
                            className="w-full h-10 px-3 rounded-md border border-border bg-card text-sm"
                        />
                    </div>

                    <div>
                        <label className="block text-xs font-medium text-muted-foreground mb-1">{t("certificado.notasLabel")}</label>
                        <textarea
                            value={notes}
                            onChange={(e) => setNotes(e.target.value)}
                            rows={2}
                            className="w-full px-3 py-2 rounded-md border border-border bg-card text-sm"
                        />
                    </div>

                    <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-500/90 flex items-start gap-2">
                        <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                        {t("certificado.avisoLegal")}
                    </div>
                </div>

                <div className="flex justify-end gap-2 mt-5">
                    <button
                        onClick={handleClose}
                        disabled={busy}
                        className="h-9 px-3 rounded-md border border-border text-sm hover:bg-muted/50"
                    >
                        {tc("cancel")}
                    </button>
                    <button
                        onClick={handleSubmit}
                        disabled={busy || !file || !password}
                        className="h-9 px-4 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:brightness-110 transition disabled:opacity-50 flex items-center gap-2"
                    >
                        {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />}
                        {t("certificado.guardarCifrado")}
                    </button>
                </div>
            </div>
        </div>
    );
}
