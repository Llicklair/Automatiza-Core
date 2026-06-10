"use client";

import type { Dispatch, SetStateAction } from "react";
import { Loader2, X, FileText, HardDrive, Folder } from "lucide-react";
import type { DriveFile } from "@/lib/api/messaging";
import { formatBytes } from "../format";

interface DrivePickerModalProps {
    setShowDrive: Dispatch<SetStateAction<boolean>>;
    driveFiles: DriveFile[] | null;
    driveLoading: boolean;
    driveQuery: string;
    setDriveQuery: Dispatch<SetStateAction<string>>;
    importingId: string | null;
    loadDrive: (q: string) => void;
    attachFromDrive: (file: DriveFile) => void;
}

export function DrivePickerModal({
    setShowDrive,
    driveFiles,
    driveLoading,
    driveQuery,
    setDriveQuery,
    importingId,
    loadDrive,
    attachFromDrive,
}: DrivePickerModalProps) {
    return (
        <div
            className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4"
            onClick={() => setShowDrive(false)}
        >
            <div
                className="bg-background border border-border rounded-xl max-w-2xl w-full max-h-[85vh] overflow-hidden flex flex-col"
                onClick={(e) => e.stopPropagation()}
            >
                <div className="flex items-center justify-between p-4 border-b border-border">
                    <h3 className="text-base font-semibold text-foreground flex items-center gap-2">
                        <HardDrive className="w-4 h-4 text-violet-400" />
                        Adjuntar desde Google Drive
                    </h3>
                    <button
                        onClick={() => setShowDrive(false)}
                        className="text-muted-foreground hover:text-foreground"
                        aria-label="Cerrar"
                    >
                        <X className="w-4 h-4" />
                    </button>
                </div>
                <div className="p-4 border-b border-border">
                    <input
                        type="text"
                        value={driveQuery}
                        onChange={(e) => setDriveQuery(e.target.value)}
                        onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); loadDrive(driveQuery); } }}
                        placeholder="Buscar archivo… (Enter para buscar)"
                        className="w-full bg-card border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-violet-500"
                    />
                </div>
                <div className="overflow-auto flex-1">
                    {driveLoading && (
                        <div className="flex items-center justify-center h-40 text-muted-foreground gap-2 text-sm">
                            <Loader2 className="w-4 h-4 animate-spin" /> Cargando…
                        </div>
                    )}
                    {!driveLoading && driveFiles?.length === 0 && (
                        <div className="flex flex-col items-center justify-center h-40 gap-2 text-muted-foreground text-sm">
                            <HardDrive className="w-7 h-7 opacity-30" />
                            Sin archivos
                        </div>
                    )}
                    {!driveLoading && driveFiles && driveFiles.length > 0 && (
                        <ul className="divide-y divide-border">
                            {driveFiles.map((f) => (
                                <li key={f.id}>
                                    <button
                                        type="button"
                                        onClick={() => attachFromDrive(f)}
                                        disabled={f.is_folder || importingId === f.id}
                                        className="w-full text-left px-4 py-3 hover:bg-muted/30 transition-colors flex items-center gap-3 disabled:opacity-50"
                                    >
                                        {f.is_folder ? <Folder className="w-4 h-4 text-muted-foreground shrink-0" /> : <FileText className="w-4 h-4 text-muted-foreground shrink-0" />}
                                        <span className="flex-1 truncate text-sm text-foreground">{f.name}</span>
                                        {f.size != null && (
                                            <span className="text-xs text-muted-foreground tabular-nums">{formatBytes(f.size)}</span>
                                        )}
                                        {importingId === f.id && <Loader2 className="w-3.5 h-3.5 animate-spin text-muted-foreground" />}
                                    </button>
                                </li>
                            ))}
                        </ul>
                    )}
                </div>
            </div>
        </div>
    );
}
