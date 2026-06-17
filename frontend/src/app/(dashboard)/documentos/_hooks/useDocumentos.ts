"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type Document as DocType } from "@/lib/api";
import { useToastStore } from "@/stores/toast";

export function useDocumentos() {
    const { show: showToast } = useToastStore();

    const [docs, setDocs]               = useState<DocType[]>([]);
    const [loading, setLoading]         = useState(false);
    const [error, setError]             = useState("");
    const [activeFolder, setActiveFolder] = useState<string | null>(null);
    const [viewMode, setViewMode]       = useState<"list" | "grid">("grid");

    // Export & Backup
    const [exportingDocs, setExportingDocs]       = useState(false);
    const [backingUp, setBackingUp]               = useState(false);
    const [restoreModalOpen, setRestoreModalOpen] = useState(false);

    const loadFolder = useCallback((folderId: string) => {
        setLoading(true);
        setError("");
        api.documents.list({ category: folderId })
            .then(setDocs)
            .catch(() => setError("Error al cargar documentos"))
            .finally(() => setLoading(false));
    }, []);

    useEffect(() => {
        if (activeFolder) loadFolder(activeFolder);
    }, [loadFolder, activeFolder]);

    async function handleExportDocs() {
        setExportingDocs(true);
        try {
            await api.documents.exportZip();
            showToast("Documentos exportados correctamente", "success");
        } catch {
            showToast("Error al exportar documentos", "error");
        } finally {
            setExportingDocs(false);
        }
    }

    async function handleBackup() {
        setBackingUp(true);
        try {
            await api.admin.downloadBackup();
            showToast("Backup descargado correctamente", "success");
        } catch {
            showToast("Error al generar el backup", "error");
        } finally {
            setBackingUp(false);
        }
    }

    return {
        docs, loading, error, activeFolder, setActiveFolder, viewMode, setViewMode,
        exportingDocs, backingUp, restoreModalOpen, setRestoreModalOpen,
        loadFolder, handleExportDocs, handleBackup,
    };
}
