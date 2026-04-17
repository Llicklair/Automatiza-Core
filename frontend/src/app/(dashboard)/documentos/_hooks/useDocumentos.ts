"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type Document as DocType } from "@/lib/api";
import { useToastStore } from "@/stores/toast";
import type { ImportResult } from "@/components/documentos/ImportDbModal";

export function useDocumentos() {
    const { show: showToast } = useToastStore();

    const [docs, setDocs]               = useState<DocType[]>([]);
    const [loading, setLoading]         = useState(false);
    const [error, setError]             = useState("");
    const [activeFolder, setActiveFolder] = useState<string | null>(null);
    const [viewMode, setViewMode]       = useState<"list" | "grid">("grid");

    // Upload modal
    const [uploadModalOpen, setUploadModalOpen]   = useState(false);
    const [uploading, setUploading]               = useState(false);
    const [dragOver, setDragOver]                 = useState(false);
    const [uploadSuccess, setUploadSuccess]       = useState("");
    const [uploadCategory, setUploadCategory]     = useState("otros");

    // Import DB modal
    const [importModalOpen, setImportModalOpen]   = useState(false);
    const [importing, setImporting]               = useState(false);
    const [importResults, setImportResults]       = useState<ImportResult[]>([]);
    const [importFiles, setImportFiles]           = useState<File[]>([]);

    // Page-level drag
    const [pageDragOver, setPageDragOver]         = useState(false);

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

    async function handleUpload(files: FileList | null) {
        if (!files || files.length === 0) return;
        setUploading(true);
        setError("");
        setUploadSuccess("");
        try {
            let count = 0;
            for (let i = 0; i < files.length; i++) {
                const file = files[i];
                if (file.name.toLowerCase().endsWith(".zip")) {
                    const extracted = await api.documents.uploadBulk(file, uploadCategory);
                    count += extracted.length;
                } else {
                    await api.documents.upload(file, uploadCategory);
                    count += 1;
                }
            }
            setUploadSuccess(`¡Se han subido y puesto en cola ${count} documento(s)!`);
            if (activeFolder === uploadCategory) loadFolder(activeFolder);
            setTimeout(() => { setUploadModalOpen(false); setUploadSuccess(""); }, 2000);
        } catch (e: any) {
            setError(e.message || "Error al subir archivos");
        } finally {
            setUploading(false);
        }
    }

    async function handleImportDB() {
        if (importFiles.length === 0) return;
        setImporting(true);
        setError("");
        setImportResults([]);
        try {
            const res = await api.documents.importDB(importFiles);
            setImportResults(res);
            setImportFiles([]);
        } catch (e: any) {
            setError(e.message || "Error al importar base de datos");
        } finally {
            setImporting(false);
        }
    }

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
        uploadModalOpen, setUploadModalOpen, uploading, dragOver, setDragOver,
        uploadSuccess, uploadCategory, setUploadCategory,
        importModalOpen, setImportModalOpen, importing, importResults, importFiles, setImportFiles,
        pageDragOver, setPageDragOver,
        exportingDocs, backingUp, restoreModalOpen, setRestoreModalOpen,
        loadFolder, handleUpload, handleImportDB, handleExportDocs, handleBackup,
    };
}
