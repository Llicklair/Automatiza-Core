"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { api } from "@/lib/api";
import { usePolling } from "@/lib/hooks/usePolling";

export type ElectronNetworkStatus = {
    localNetworkEnabled: boolean;
    lanIP: string;
    urls?: { local?: string; lan?: string };
};

export type ScanResult = {
    document: { id: string; file_name: string; file_type: string | null; file_size: number; status: string; category: string | null };
    auto_category: string;
    message: string;
};

export function formatSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function getElectronAPI() {
    if (typeof window === "undefined") return null;
    return (window as unknown as { electronAPI?: {
        toggleLocalNetwork?: (enabled: boolean) => Promise<{ ok?: boolean; error?: string }>;
        getNetworkStatus?: () => Promise<ElectronNetworkStatus>;
    } }).electronAPI ?? null;
}

export function useEscaner() {
    const [scanning, setScanning] = useState(false);
    const [results, setResults] = useState<ScanResult[]>([]);
    const [error, setError] = useState("");
    const [dragOver, setDragOver] = useState(false);
    const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
    const [docStatuses, setDocStatuses] = useState<Record<string, { status: string; category: string | null }>>({});
    const fileInputRef = useRef<HTMLInputElement>(null);

    const [netStatus, setNetStatus] = useState<ElectronNetworkStatus | null>(null);
    const [netToggling, setNetToggling] = useState(false);

    useEffect(() => {
        const electronApi = getElectronAPI();
        if (!electronApi?.getNetworkStatus) return;
        void electronApi.getNetworkStatus().then(setNetStatus).catch(() => {});
    }, []);

    async function handleLanToggle(next: boolean) {
        const electronApi = getElectronAPI();
        if (!electronApi?.toggleLocalNetwork) return;
        setNetToggling(true);
        try {
            const res = await electronApi.toggleLocalNetwork(next);
            if (res?.ok !== false && electronApi.getNetworkStatus) {
                const s = await electronApi.getNetworkStatus();
                setNetStatus(s);
            }
        } finally {
            setNetToggling(false);
        }
    }

    // Polling: actualizar estado de documentos que estan procesando
    const processing = results.filter(r => {
        const st = docStatuses[r.document.id];
        return !st || st.status === "processing" || st.status === "uploaded";
    });

    usePolling(async () => {
        try {
            const allDocs = await api.documents.list({});
            const statusMap: Record<string, { status: string; category: string | null }> = {};
            for (const doc of allDocs) {
                statusMap[doc.id] = { status: doc.status, category: doc.category };
            }
            setDocStatuses(prev => ({ ...prev, ...statusMap }));
        } catch {
            // silenciar errores de polling
        }
    }, 4000, { enabled: processing.length > 0 });

    const handleFiles = useCallback((files: FileList | null) => {
        if (!files || files.length === 0) return;
        setSelectedFiles(prev => [...prev, ...Array.from(files)]);
        setError("");
    }, []);

    const removeFile = (index: number) => {
        setSelectedFiles(prev => prev.filter((_, i) => i !== index));
    };

    async function handleScan() {
        if (selectedFiles.length === 0) return;
        setScanning(true);
        setError("");
        setResults([]);

        try {
            const res = await api.documents.scan(selectedFiles);
            setResults(res);
            setSelectedFiles([]);
        } catch (e: any) {
            setError(e.message || "Error al escanear archivos");
        } finally {
            setScanning(false);
        }
    }

    const grouped = results.reduce<Record<string, ScanResult[]>>((acc, r) => {
        const cat = r.auto_category;
        if (!acc[cat]) acc[cat] = [];
        acc[cat].push(r);
        return acc;
    }, {});

    return {
        scanning, results, error, dragOver, setDragOver,
        selectedFiles, docStatuses, fileInputRef,
        netStatus, netToggling, handleLanToggle,
        handleFiles, removeFile, handleScan, grouped,
    };
}
