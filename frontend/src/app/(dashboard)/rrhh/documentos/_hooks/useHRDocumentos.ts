"use client";

import { useEffect, useState, useCallback } from "react";
import { hrDocuments } from "@/lib/api/hr_documents";
import type { HRDocument } from "@/lib/api/hr_documents";
import { logError } from "@/lib/logger";

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

export const DOC_TYPES = [
    { value: "contract", label: "Contrato de trabajo" },
    { value: "nda", label: "Acuerdo de Confidencialidad (NDA)" },
    { value: "termination", label: "Carta de despido" },
    { value: "settlement", label: "Finiquito" },
    { value: "addendum", label: "Adenda contractual" },
    { value: "other", label: "Otro documento laboral" },
];

export const DOC_TEMPLATES: Record<string, string> = {
    contract:
`Tipo de contrato: indefinido / temporal (indica cuál).
Jornada: completa 40h/semana / parcial [X]h/semana.
Salario bruto anual: [X €] / mensual: [X €].
Puesto: [nombre del puesto].
Departamento: [departamento].
Fecha de incorporación: [DD/MM/AAAA].
Centro de trabajo: [ciudad].
Período de prueba: [X meses] (máx. 6 meses técnicos, 2 meses resto).`,

    nda:
`Partes: la empresa y [nombre del trabajador / colaborador].
Información confidencial que se protege: [describir — código fuente, clientes, estrategia, etc.].
Duración de la obligación: [X años tras fin de relación laboral].
Ámbito geográfico: [nacional / internacional].
Consecuencias de incumplimiento: [indemnización / acciones legales].`,

    termination:
`Tipo de despido: disciplinario / objetivo / colectivo.
Motivo: [describir causa concreta].
Fecha efectiva del despido: [DD/MM/AAAA].
Preaviso: [X días / no aplica despido disciplinario].
Indemnización: [según ley: 20 días/año objetivo | 33 días/año improcedente | 0 disciplinario].
Acumulación de vacaciones pendientes: [X días].`,

    settlement:
`Fecha de baja: [DD/MM/AAAA].
Motivo de la baja: [despido / renuncia voluntaria / fin de contrato].
Salario pendiente del mes en curso (días trabajados): [X €].
Vacaciones no disfrutadas: [X días = X €].
Pagas extras proporcionales pendientes: [X €].
Indemnización (si aplica): [X €].`,

    addendum:
`Contrato original fecha: [DD/MM/AAAA].
Cláusula(s) que se modifican: [describir qué cambia].
Nueva condición: [texto de la nueva cláusula].
Motivo del cambio: [acuerdo mutuo / cambio de funciones / ascenso / etc.].
Fecha de entrada en vigor: [DD/MM/AAAA].`,

    other:
`Describe el documento que necesitas:
Partes involucradas: [nombres y roles].
Objeto del documento: [qué regula o certifica].
Condiciones principales: [listar].
Fecha: [DD/MM/AAAA].`,
};

export function useHRDocumentos() {
    const [docs, setDocs]             = useState<HRDocument[]>([]);
    const [loading, setLoading]       = useState(true);
    const [generating, setGenerating] = useState(false);
    const [error, setError]           = useState<string | null>(null);
    const [toast, setToast]           = useState<string | null>(null);
    const [form, setForm]             = useState({ doc_type: "contract", employee_name: "", instructions: DOC_TEMPLATES["contract"] });
    const [nlText, setNlText]         = useState("");
    const [nlGenerating, setNlGenerating] = useState(false);

    const showToast = (msg: string) => { setToast(msg); setTimeout(() => setToast(null), 3500); };

    const loadDocs = useCallback(async () => {
        try { setDocs(await hrDocuments.list({ limit: 50 })); }
        catch (err) { logError("rrhh/documentos", err); setError("No se pudieron cargar los documentos"); }
    }, []);

    useEffect(() => { setLoading(true); loadDocs().finally(() => setLoading(false)); }, [loadDocs]);

    const handleNLGenerate = async () => {
        if (!nlText.trim()) return;
        setNlGenerating(true); setError(null);
        try {
            const parsed = parseNLIntent(nlText.trim());
            const doc = await hrDocuments.generate({
                doc_type: parsed.doc_type,
                employee_name: parsed.employee_name || undefined,
                instructions: parsed.instructions || nlText.trim(),
            });
            setDocs(prev => [doc, ...prev]);
            setNlText("");
            showToast("Borrador generado");
        } catch (e: any) { setError(e?.message ?? "Error al generar"); }
        finally { setNlGenerating(false); }
    };

    const handleGenerate = async () => {
        if (!form.doc_type) { setError("Selecciona el tipo de documento"); return; }
        setGenerating(true); setError(null);
        try {
            const doc = await hrDocuments.generate({
                doc_type: form.doc_type,
                employee_name: form.employee_name.trim() || undefined,
                instructions: form.instructions.trim(),
            });
            setDocs(prev => [doc, ...prev]);
            setForm(f => ({ ...f, employee_name: "", instructions: "" }));
            showToast("Borrador generado");
        } catch (e: any) { setError(e?.message ?? "Error al generar"); }
        finally { setGenerating(false); }
    };

    const handleApprove = async (id: string) => {
        try { await hrDocuments.approve(id); setDocs(prev => prev.map(d => d.id === id ? { ...d, status: "approved" as const } : d)); showToast("Documento aprobado"); }
        catch { showToast("Error al aprobar"); }
    };

    const handleDelete = async (id: string) => {
        try { await hrDocuments.delete(id); setDocs(prev => prev.filter(d => d.id !== id)); showToast("Eliminado"); }
        catch { showToast("Error al eliminar"); }
    };

    return {
        docs, loading, generating, error, toast,
        form, setForm,
        nlText, setNlText, nlGenerating,
        handleNLGenerate, handleGenerate, handleApprove, handleDelete,
    };
}
