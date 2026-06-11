"use client";

import { useEffect, useState } from "react";
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

function formatAge(hours: number): string {
    if (hours < 1) return `${Math.round(hours * 60)} min`;
    if (hours < 24) return `${hours.toFixed(1)} h`;
    return `${(hours / 24).toFixed(1)} días`;
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
            toast.error("No se pudieron cargar los backups: " + msg);
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
                toast.success("Backup creado correctamente");
                await reload();
            } else if (result.status === "disabled") {
                toast.warning("Los backups están desactivados (BACKUP_ENABLED=false)");
            } else {
                toast.error("El backup falló — revisa los logs del servidor");
            }
        } catch (e) {
            toast.error("Error: " + (e instanceof Error ? e.message : String(e)));
        } finally {
            setCreating(false);
        }
    };

    const onDownload = async (file: string) => {
        setBusyFile(file);
        try {
            await system.downloadBackup(file);
            toast.success("Descarga iniciada");
        } catch (e) {
            toast.error("Error al descargar: " + (e instanceof Error ? e.message : String(e)));
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
                    toast.success("BD restaurada correctamente");
                } else {
                    toast.error("La restauración falló: " + (result.error ?? "error desconocido"));
                }
            } else {
                await system.deleteBackup(file);
                toast.success("Backup borrado");
                await reload();
            }
        } catch (e) {
            toast.error("Error: " + (e instanceof Error ? e.message : String(e)));
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
                            Copias de seguridad
                        </CardTitle>
                        <p className="mt-1 text-sm text-muted-foreground">
                            Backups automáticos diarios a las 04:00. Retención 7 días.
                        </p>
                    </div>
                    <Button onClick={onCreate} disabled={creating}>
                        {creating ? (
                            <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                        ) : (
                            <Database className="mr-2 h-4 w-4" />
                        )}
                        Crear backup ahora
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
                            No hay backups todavía. Crea uno manualmente o espera al job
                            automático de las 04:00.
                        </p>
                    ) : (
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Archivo</TableHead>
                                    <TableHead>Tamaño</TableHead>
                                    <TableHead>Antigüedad</TableHead>
                                    <TableHead>Creado</TableHead>
                                    <TableHead className="text-right">Acciones</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {items.map((b) => (
                                    <TableRow key={b.filename}>
                                        <TableCell className="font-mono text-xs">
                                            {b.filename}
                                        </TableCell>
                                        <TableCell>{b.size_mb} MB</TableCell>
                                        <TableCell>{formatAge(b.age_hours)}</TableCell>
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
                                                    title="Descargar a disco"
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
                                                    title="Restaurar (destructivo)"
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
                                                    title="Borrar"
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
                                ? "Restaurar copia de seguridad"
                                : "Borrar copia de seguridad"}
                        </DialogTitle>
                        <DialogDescription>
                            {confirm.kind === "restore" ? (
                                <span className="block space-y-2">
                                    <span className="block text-destructive font-medium">
                                        ATENCIÓN: operación destructiva.
                                    </span>
                                    <span className="block">
                                        Vas a restaurar la BD desde{" "}
                                        <span className="font-mono text-xs">{confirm.file}</span>.
                                        Los datos actuales se sobrescribirán. Asegúrate de tener un
                                        backup más reciente descargado antes de continuar.
                                    </span>
                                </span>
                            ) : (
                                <>
                                    Vas a borrar el archivo{" "}
                                    <span className="font-mono text-xs">{confirm.file}</span> del
                                    disco. Esta acción no se puede deshacer.
                                </>
                            )}
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                        <Button
                            variant="outline"
                            onClick={() => setConfirm({ kind: null, file: "" })}
                        >
                            Cancelar
                        </Button>
                        <Button variant="destructive" onClick={onConfirm}>
                            {confirm.kind === "restore" ? "Restaurar" : "Borrar"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </PageContainer>
    );
}
