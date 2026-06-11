"use client";

import { useRef, useState } from "react";
import { useTranslations } from "next-intl";
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
    const t = useTranslations("rrhh");
    const fileRef  = useRef<HTMLInputElement>(null);
    const [dragging, setDragging]   = useState(false);
    const [analyzing, setAnalyzing] = useState(false);
    const [result, setResult]       = useState<CVAnalysisResult | null>(null);
    const [error, setError]         = useState<string | null>(null);
    const [fileName, setFileName]   = useState<string | null>(null);
    // Conservamos el File analizado para poder crear el candidato en una vacante
    // sin volver a pedirlo (el flujo conectado lo reusa vía uploadCV).
    const [file, setFile]           = useState<File | null>(null);

    const analyzeFile = async (f: File) => {
        if (!f.name.toLowerCase().endsWith(".pdf")) { setError(t("analisisCv.onlyPdfError")); return; }
        setAnalyzing(true); setError(null); setResult(null); setFileName(f.name); setFile(f);
        try {
            const form = new FormData();
            form.append("file", f);
            const data = await requestUpload<CVAnalysisResult>("/api/v1/recruitment/analyze-cv", form);
            setResult(data);
        } catch (e: any) { setError(e?.message ?? t("analisisCv.analyzeError")); setFile(null); }
        finally { setAnalyzing(false); }
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const f = e.target.files?.[0];
        if (f) analyzeFile(f);
        if (fileRef.current) fileRef.current.value = "";
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setDragging(false);
        const f = e.dataTransfer.files?.[0];
        if (f) analyzeFile(f);
    };

    const reset = () => { setResult(null); setError(null); setFileName(null); setFile(null); };

    return {
        fileRef,
        dragging, setDragging,
        analyzing,
        result,
        error,
        fileName,
        file,
        handleFileChange,
        handleDrop,
        triggerFileInput: () => fileRef.current?.click(),
        reset,
    };
}
