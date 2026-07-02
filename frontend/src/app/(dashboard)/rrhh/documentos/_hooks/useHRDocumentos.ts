"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { hrDocuments } from "@/lib/api/hr_documents";
import type { HRDocument } from "@/lib/api/hr_documents";
import { logError } from "@/lib/logger";
import { useToastStore } from "@/stores/toast";

export function parseNLIntent(text: string): { doc_type: string; employee_name: string; instructions: string } {
    const t = text.toLowerCase();
    let doc_type = "other";
    if (/contrato|contrataci[oó]n|trabajo/.test(t))  doc_type = "contract";
    else if (/nda|confidencial|no divulg/.test(t))   doc_type = "nda";
    else if (/despido|despedido|terminaci[oó]n/.test(t)) doc_type = "termination";
    else if (/finiquito|liquidaci[oó]n/.test(t))     doc_type = "settlement";
    else if (/adenda|addendum|modificaci[oó]n/.test(t)) doc_type = "addendum";

    const nameMatch = text.match(/para\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*)/i);
    const employee_name = nameMatch ? nameMatch[1] : "";
    const instructions = text.replace(/para\s+\S+(\s+\S+)?/i, "").replace(/(contrato|nda|despido|finiquito|adenda|documento|quiero|necesito|genera|crea)/gi, "").trim();

    return { doc_type, employee_name, instructions };
}

// I18N — config estructural + labelKey; el componente traduce en render.
export const DOC_TYPES = [
    { value: "contract", labelKey: "documentos.types.contract" },
    { value: "nda", labelKey: "documentos.types.nda" },
    { value: "termination", labelKey: "documentos.types.termination" },
    { value: "settlement", labelKey: "documentos.types.settlement" },
    { value: "addendum", labelKey: "documentos.types.addendum" },
    { value: "other", labelKey: "documentos.types.other" },
];

// Plantillas de instrucciones (texto editable visible en la UI) → claves i18n.
export const DOC_TEMPLATE_KEYS: Record<string, string> = {
    contract: "documentos.templates.contract",
    nda: "documentos.templates.nda",
    termination: "documentos.templates.termination",
    settlement: "documentos.templates.settlement",
    addendum: "documentos.templates.addendum",
    other: "documentos.templates.other",
};

export function useHRDocumentos() {
    const t = useTranslations("rrhh");
    const [docs, setDocs]             = useState<HRDocument[]>([]);
    const [loading, setLoading]       = useState(true);
    const [generating, setGenerating] = useState(false);
    const [error, setError]           = useState<string | null>(null);
    const [form, setForm]             = useState(() => ({ doc_type: "contract", employee_name: "", instructions: t(DOC_TEMPLATE_KEYS["contract"]) }));
    const [nlText, setNlText]         = useState("");
    const searchParams = useSearchParams();
    // Permite llegar pre-filtrado desde la ficha de empleado (?employee=<nombre>).
    const [employeeFilter, setEmployeeFilter] = useState(searchParams.get("employee") ?? "");

    const filteredDocs = useMemo(() => {
        const term = employeeFilter.trim().toLowerCase();
        if (!term) return docs;
        return docs.filter(d => (d.employee_name ?? "").toLowerCase().includes(term));
    }, [docs, employeeFilter]);

    const loadDocs = useCallback(async () => {
        try { setDocs(await hrDocuments.list({ limit: 50 })); }
        catch (err) { logError("rrhh/documentos", err); setError(t("documentos.loadError")); }
    }, [t]);

    useEffect(() => { setLoading(true); loadDocs().finally(() => setLoading(false)); }, [loadDocs]);

    // La barra NL no genera directo: interpreta y rellena el formulario para que
    // el usuario confirme (parseNLIntent es heurístico y puede equivocarse).
    const handleNLGenerate = () => {
        if (!nlText.trim()) return;
        setError(null);
        const parsed = parseNLIntent(nlText.trim());
        setForm({
            doc_type: parsed.doc_type,
            employee_name: parsed.employee_name,
            instructions: parsed.instructions || nlText.trim(),
        });
        setNlText("");
        useToastStore.getState().success(t("documentos.nlFilledToast"));
    };

    const handleGenerate = async () => {
        if (!form.doc_type) { setError(t("documentos.selectTypeError")); return; }
        setGenerating(true); setError(null);
        try {
            const doc = await hrDocuments.generate({
                doc_type: form.doc_type,
                employee_name: form.employee_name.trim() || undefined,
                instructions: form.instructions.trim(),
            });
            setDocs(prev => [doc, ...prev]);
            setForm(f => ({ ...f, employee_name: "", instructions: "" }));
            useToastStore.getState().success(t("toasts.draftGenerated"));
        } catch (e: any) { setError(e?.message ?? t("documentos.generateError")); }
        finally { setGenerating(false); }
    };

    const handleApprove = async (id: string) => {
        try { const res = await hrDocuments.approve(id); setDocs(prev => prev.map(d => d.id === id ? { ...d, status: "approved" as const, doc_number: res.doc_number } : d)); useToastStore.getState().success(t("toasts.documentApproved")); }
        catch { useToastStore.getState().error(t("toasts.documentApproveError")); }
    };

    const handleDelete = async (id: string) => {
        try { await hrDocuments.delete(id); setDocs(prev => prev.filter(d => d.id !== id)); useToastStore.getState().success(t("toasts.deleted")); }
        catch { useToastStore.getState().error(t("toasts.deleteError")); }
    };

    return {
        docs: filteredDocs, loading, generating, error,
        form, setForm,
        nlText, setNlText,
        employeeFilter, setEmployeeFilter,
        handleNLGenerate, handleGenerate, handleApprove, handleDelete,
    };
}
