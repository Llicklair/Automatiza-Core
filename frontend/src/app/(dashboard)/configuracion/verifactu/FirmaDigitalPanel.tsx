"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import {
    AlertTriangle, CheckCircle2, FileKey2, Loader2, ShieldCheck, Trash2, Upload,
} from "lucide-react";
import { api } from "@/lib/api";
import type { CertificateStatus } from "@/lib/api";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { useToastStore } from "@/stores/toast";
import { showConfirm } from "@/stores/confirm";

const fmtDate = (d: string) =>
    new Date(d).toLocaleDateString("es-ES", { day: "2-digit", month: "long", year: "numeric" });

function isExpired(d: string) {
    return new Date(d) < new Date();
}

function isExpiringSoon(d: string) {
    const diff = new Date(d).getTime() - Date.now();
    return diff > 0 && diff < 30 * 24 * 60 * 60 * 1000;
}

export function FirmaDigitalPanel() {
    const t = useTranslations("configuracion");
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
            toast.error(t("verifactu.errorLoadCert"));
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
            toast.error(e?.message ?? t("verifactu.errorUploadCert"));
        } finally {
            setIsUploading(false);
        }
    };

    const handleDelete = async () => {
        if (!(await showConfirm({
            message: t("verifactu.confirmDeleteCert"),
            confirmLabel: t("verifactu.deleteAction"),
            confirmVariant: "danger",
        }))) return;
        setIsDeleting(true);
        try {
            await api.tenant.certificate.delete();
            toast.success(t("verifactu.certDeleted"));
            await load();
        } catch {
            toast.error(t("verifactu.errorDeleteCert"));
        } finally {
            setIsDeleting(false);
        }
    };

    return (
        <div className="space-y-6">
            <PageHeader
                title={t("verifactu.firmaTitle")}
                description={t("verifactu.firmaDesc")}
                icon={FileKey2}
            />

            {/* Current cert status */}
            <div className="rounded-xl border border-border bg-card p-5 space-y-4">
                <h2 className="text-sm font-semibold text-foreground">{t("verifactu.activeCert")}</h2>

                {isLoading ? (
                    <div className="flex items-center gap-2 text-muted-foreground text-sm">
                        <Loader2 className="w-4 h-4 animate-spin" /> {t("verifactu.loading")}
                    </div>
                ) : !status?.has_certificate ? (
                    <div className="flex items-center gap-3 text-muted-foreground text-sm">
                        <ShieldCheck className="w-5 h-5 opacity-40" />
                        <span>{t("verifactu.noCert")}</span>
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
                                        {t("verifactu.expiresOn", { date: fmtDate(status.cert_expires_at) })}
                                        {isExpired(status.cert_expires_at) && ` — ${t("verifactu.expired")}`}
                                        {isExpiringSoon(status.cert_expires_at) && ` — ${t("verifactu.expiringSoon")}`}
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
                            {t("verifactu.deleteCert")}
                        </Button>
                    </div>
                )}
            </div>

            {/* Upload new cert */}
            <div className="rounded-xl border border-border bg-card p-5 space-y-4">
                <h2 className="text-sm font-semibold text-foreground">
                    {status?.has_certificate ? t("verifactu.replaceCert") : t("verifactu.loadCert")}
                </h2>
                <p className="text-xs text-muted-foreground">
                    {t.rich("verifactu.uploadHint", {
                        strong: (chunks) => <strong>{chunks}</strong>,
                    })}
                </p>

                <div className="space-y-3">
                    <div>
                        <label className="text-xs text-muted-foreground block mb-1.5">{t("verifactu.fileLabel")}</label>
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
                        <label className="text-xs text-muted-foreground block mb-1.5">{t("verifactu.certPasswordLabel")}</label>
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder={t("verifactu.certPasswordPlaceholder")}
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
                            ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />{t("verifactu.validatingSaving")}</>
                            : <><Upload className="mr-2 h-4 w-4" />{t("verifactu.loadCert")}</>}
                    </Button>
                </div>
            </div>

            <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 px-4 py-3 text-xs text-amber-400 space-y-1">
                <p className="font-medium flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5" /> {t("verifactu.securityNote")}
                </p>
                <p>
                    {t("verifactu.securityNoteDesc")}
                </p>
            </div>
        </div>
    );
}
