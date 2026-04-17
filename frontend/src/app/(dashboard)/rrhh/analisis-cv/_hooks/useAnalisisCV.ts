"use client";

import { useRef, useState } from "react";
import { requestUpload } from "@/lib/api/client";

export interface CVAnalysisResult {
    name: string | null;
    email: string | null;
    phone: string | null;
    skills: string[];
    experience_years: number | null;
    education: string | null;
    languages: Array<string | { lang: string; level?: string }>;
    summary: string | null;
}

export function useAnalisisCV() {
    const fileRef  = useRef<HTMLInputElement>(null);
    const [dragging, setDragging]   = useState(false);
    const [analyzing, setAnalyzing] = useState(false);
    const [result, setResult]       = useState<CVAnalysisResult | null>(null);
    const [error, setError]         = useState<string | null>(null);
    const [fileName, setFileName]   = useState<string | null>(null);

    const analyzeFile = async (file: File) => {
        if (!file.name.toLowerCase().endsWith(".pdf")) { setError("Solo se aceptan archivos PDF"); return; }
        setAnalyzing(true); setError(null); setResult(null); setFileName(file.name);
        try {
            const form = new FormData();
            form.append("file", file);
            const data = await requestUpload<CVAnalysisResult>("/api/v1/recruitment/analyze-cv", form);
            setResult(data);
        } catch (e: any) { setError(e?.message ?? "Error al analizar el CV"); }
        finally { setAnalyzing(false); }
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) analyzeFile(file);
        if (fileRef.current) fileRef.current.value = "";
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setDragging(false);
        const f = e.dataTransfer.files?.[0];
        if (f) analyzeFile(f);
    };

    return {
        fileRef,
        dragging, setDragging,
        analyzing,
        result,
        error,
        fileName,
        handleFileChange,
        handleDrop,
        triggerFileInput: () => fileRef.current?.click(),
    };
}
