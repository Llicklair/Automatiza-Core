"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
type T = ReturnType<typeof useTranslations>;
import { Database, Download, RefreshCw, Trash2, Upload } from "lucide-react";
import { useToastStore } from "@/stores/toast";

import { system, type BackupItem } from "@/lib/api/system";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { PageContainer } from "@/components/shared/PageContainer";

type ConfirmKind = null | "restore" | "delete";

function formatAge(hours: number, t: T): string {
    if (hours < 1) return t("backups.ageMin", { value: Math.round(hours * 60) });
    if (hours < 24) return t("backups.ageHours", { value: hours.toFixed(1) });
    return t("backups.ageDays", { value: (hours / 24).toFixed(1) });
}

function formatDate(iso: string): string {
    try {
        return new Date(iso).toLocaleString("es-ES", {
            dateStyle: "short",
            timeStyle: "short",
        });
    } catch {
        return iso;
    }
}

export default function BackupsPage() {
    const t = useTranslations("configuracion");
    const tc = useTranslations("common");
    const toast = useToastStore();
    const [items, setItems] = useState<BackupItem[] | null>(null);
    const [creating, setCreating] = useState(false);
    const [busyFile, setBusyFile] = useState<string | null>(null);
    const [confirm, setConfirm] = useState<{ kind: ConfirmKind; file: string }>({
        kind: null,
        file: "",
    });

    const reload = async () => {
        try {
            setItems(await system.listBackups());
        } catch (e) {
            const msg = e instanceof Error ? e.message : String(e);
            toast.error(t("backups.loadError", { message: msg }));
            setItems([]);
        }
    };

    useEffect(() => {
        reload();
    }, []);

    const onCreate = async () => {
        setCreating(true);
        try {
            const result = await system.runBackup();
            if (result.status === "ok") {
                toast.success(t("backups.createOk"));
                await reload();
            } else if (result.status === "disabled") {
                toast.warning(t("backups.disabled"));
            } else {
                toast.error(t("backups.createFailed"));
            }
        } catch (e) {
            toast.error(t("backups.error", { message: e instanceof Error ? e.message : String(e) }));
        } finally {
            setCreating(false);
        }
    };

    const onDownload = async (file: string) => {
        setBusyFile(file);
        try {
            await system.downloadBackup(file);
            toast.success(t("backups.downloadStarted"));
        } catch (e) {
            toast.error(t("backups.downloadError", { message: e instanceof Error ? e.message : String(e) }));
        } finally {
            setBusyFile(null);
        }
    };

    const onConfirm = async () => {
        const file = confirm.file;
        const kind = confirm.kind;
        setConfirm({ kind: null, file: "" });
        if (!kind) return;

        setBusyFile(file);
        try {
            if (kind === "restore") {
                const result = await system.restoreBackup(file);
                if (result.status === "ok") {
                    toast.success(t("backups.restoreOk"));
                } else {
                    toast.error(t("backups.restoreFailed", { error: result.error ?? t("backups.unknownError") }));
                }
            } else {
                await system.deleteBackup(file);
                toast.success(t("backups.deleteOk"));
                await reload();
            }
        } catch (e) {
            toast.error(t("backups.error", { message: e instanceof Error ? e.message : String(e) }));
        } finally {
            setBusyFile(null);
        }
    };

    return (
        <PageContainer width="full">
            <Card>
                <CardHeader className="flex flex-row items-center justify-between gap-4">
                    <div>
                        <CardTitle className="flex items-center gap-2">
                            <Database className="h-5 w-5" />
                            {t("backups.title")}
                        </CardTitle>
                        <p className="mt-1 text-sm text-muted-foreground">
                            {t("backups.subtitle")}
                        </p>
                    </div>
                    <Button onClick={onCreate} disabled={creating}>
                        {creating ? (
                            <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                        ) : (
                            <Database className="mr-2 h-4 w-4" />
                        )}
                        {t("backups.createNow")}
                    </Button>
                </CardHeader>
                <CardContent>
                    {items === null ? (
                        <div className="space-y-2">
                            <Skeleton className="h-10 w-full" />
                            <Skeleton className="h-10 w-full" />
                            <Skeleton className="h-10 w-full" />
                        </div>
                    ) : items.length === 0 ? (
                        <p className="py-8 text-center text-sm text-muted-foreground">
                            {t("backups.empty")}
                        </p>
                    ) : (
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>{t("backups.colFile")}</TableHead>
                                    <TableHead>{t("backups.colSize")}</TableHead>
                                    <TableHead>{t("backups.colAge")}</TableHead>
                                    <TableHead>{t("backups.colCreated")}</TableHead>
                                    <TableHead className="text-right">{t("backups.colActions")}</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {items.map((b) => (
                                    <TableRow key={b.filename}>
                                        <TableCell className="font-mono text-xs">
                                            {b.filename}
                                        </TableCell>
                                        <TableCell>{b.size_mb} MB</TableCell>
                                        <TableCell>{formatAge(b.age_hours, t)}</TableCell>
                                        <TableCell className="text-sm">
                                            {formatDate(b.created_at)}
                                        </TableCell>
                                        <TableCell className="text-right">
                                            <div className="inline-flex gap-2">
                                                <Button
                                                    size="sm"
                                                    variant="outline"
                                                    disabled={busyFile === b.filename}
                                                    onClick={() => onDownload(b.filename)}
                                                    title={t("backups.downloadTitle")}
                                                >
                                                    <Download className="h-4 w-4" />
                                                </Button>
                                                <Button
                                                    size="sm"
                                                    variant="outline"
                                                    disabled={busyFile === b.filename}
                                                    onClick={() =>
                                                        setConfirm({ kind: "restore", file: b.filename })
                                                    }
                                                    title={t("backups.restoreTitle")}
                                                >
                                                    <Upload className="h-4 w-4" />
                                                </Button>
                                                <Button
                                                    size="sm"
                                                    variant="destructive"
                                                    disabled={busyFile === b.filename}
                                                    onClick={() =>
                                                        setConfirm({ kind: "delete", file: b.filename })
                                                    }
                                                    title={t("backups.deleteTitle")}
                                                >
                                                    <Trash2 className="h-4 w-4" />
                                                </Button>
                                            </div>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    )}
                </CardContent>
            </Card>

            <Dialog
                open={confirm.kind !== null}
                onOpenChange={(open) =>
                    setConfirm({ kind: open ? confirm.kind : null, file: confirm.file })
                }
            >
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>
                            {confirm.kind === "restore"
                                ? t("backups.restoreDialogTitle")
                                : t("backups.deleteDialogTitle")}
                        </DialogTitle>
                        <DialogDescription>
                            {confirm.kind === "restore" ? (
                                <span className="block space-y-2">
                                    <span className="block text-destructive font-medium">
                                        {t("backups.restoreDialogWarning")}
                                    </span>
                                    <span className="block">
                                        {t.rich("backups.restoreDialogBody", {
                                            file: confirm.file,
                                            mono: (chunks) => <span className="font-mono text-xs">{chunks}</span>,
                                        })}
                                    </span>
                                </span>
                            ) : (
                                <>
                                    {t.rich("backups.deleteDialogBody", {
                                        file: confirm.file,
                                        mono: (chunks) => <span className="font-mono text-xs">{chunks}</span>,
                                    })}
                                </>
                            )}
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                        <Button
                            variant="outline"
                            onClick={() => setConfirm({ kind: null, file: "" })}
                        >
                            {tc("cancel")}
                        </Button>
                        <Button variant="destructive" onClick={onConfirm}>
                            {confirm.kind === "restore" ? t("backups.restoreAction") : t("backups.deleteAction")}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </PageContainer>
    );
}
