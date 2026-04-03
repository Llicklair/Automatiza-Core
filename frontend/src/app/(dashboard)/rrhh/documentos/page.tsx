"use client";

import { useEffect, useState, useCallback } from "react";
import { hrDocuments } from "@/lib/api/hr_documents";
import type { HRDocument } from "@/lib/api/hr_documents";
import { FileText, Plus, CheckCircle2, Trash2, Copy, Loader2, X, ChevronDown, ChevronUp, Send, Wand2 } from "lucide-react";

// Parser de lenguaje natural → campos del documento
function parseNLIntent(text: string): { doc_type: string; employee_name: string; instructions: string } {
    const t = text.toLowerCase();
    let doc_type = "other";
    if (/contrato|contrataci[oó]n|trabajo/.test(t))  doc_type = "contract";
    else if (/nda|confidencial|no divulg/.test(t))   doc_type = "nda";
    else if (/despido|despedido|terminaci[oó]n/.test(t)) doc_type = "termination";
    else if (/finiquito|liquidaci[oó]n/.test(t))     doc_type = "settlement";
    else if (/adenda|addendum|modificaci[oó]n/.test(t)) doc_type = "addendum";

    // Extraer nombre: "para [Nombre Apellido]"
    const nameMatch = text.match(/para\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*)/i);
    const employee_name = nameMatch ? nameMatch[1] : "";

    // Instrucciones: el resto del texto
    const instructions = text.replace(/para\s+\S+(\s+\S+)?/i, "").replace(/(contrato|nda|despido|finiquito|adenda|documento|quiero|necesito|genera|crea)/gi, "").trim();

    return { doc_type, employee_name, instructions };
}

const DOC_TYPES = [
    { value: "contract", label: "Contrato de trabajo" },
    { value: "nda", label: "Acuerdo de Confidencialidad (NDA)" },
    { value: "termination", label: "Carta de despido" },
    { value: "settlement", label: "Finiquito" },
    { value: "addendum", label: "Adenda contractual" },
    { value: "other", label: "Otro documento laboral" },
];

function StatusBadge({ status }: { status: HRDocument["status"] }) {
    return status === "approved" ? (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3 h-3" /> Aprobado
        </span>
    ) : (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
            Borrador
        </span>
    );
}

function DocumentCard({ doc, onApprove, onDelete }: {
    doc: HRDocument; onApprove: (id: string) => void; onDelete: (id: string) => void;
}) {
    const [expanded, setExpanded] = useState(false);
    const [copying, setCopying] = useState(false);
    const docTypeLabel = DOC_TYPES.find(t => t.value === doc.doc_type)?.label ?? doc.doc_type;
    const date = new Date(doc.created_at).toLocaleDateString("es-ES", { day: "numeric", month: "short", year: "numeric" });

    const handleCopy = async () => {
        setCopying(true);
        await navigator.clipboard.writeText(doc.content_html).catch(() => {});
        setTimeout(() => setCopying(false), 1500);
    };

    return (
        <div className="bg-[#18181b] border border-[#27272a] rounded-xl overflow-hidden">
            <div className="p-4 flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="text-sm font-medium text-white truncate">{doc.title}</h3>
                        <StatusBadge status={doc.status} />
                    </div>
                    <p className="text-xs text-zinc-500 mt-1">{docTypeLabel} · {doc.employee_name} · {date}</p>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                    <button onClick={handleCopy} title="Copiar HTML"
                        className="p-1.5 rounded-lg text-zinc-600 hover:text-zinc-300 hover:bg-zinc-800 transition-colors">
                        {copying ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                    </button>
                    {doc.status === "draft" && (
                        <button onClick={() => onApprove(doc.id)} title="Aprobar"
                            className="p-1.5 rounded-lg text-emerald-400 hover:bg-emerald-500/10 transition-colors">
                            <CheckCircle2 className="w-4 h-4" />
                        </button>
                    )}
                    <button onClick={() => onDelete(doc.id)} title="Eliminar"
                        className="p-1.5 rounded-lg text-red-400 hover:bg-red-500/10 transition-colors">
                        <Trash2 className="w-4 h-4" />
                    </button>
                    <button onClick={() => setExpanded(v => !v)}
                        className="p-1.5 rounded-lg text-zinc-600 hover:bg-zinc-800 transition-colors">
                        {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </button>
                </div>
            </div>
            {expanded && (
                <div className="border-t border-[#27272a] p-4 bg-[#09090b]">
                    <div className="prose prose-invert prose-sm max-w-none text-zinc-300"
                        dangerouslySetInnerHTML={{ __html: doc.content_html }} />
                </div>
            )}
        </div>
    );
}

export default function HRDocumentosPage() {
    const [docs, setDocs]             = useState<HRDocument[]>([]);
    const [loading, setLoading]       = useState(true);
    const [generating, setGenerating] = useState(false);
    const [error, setError]           = useState<string | null>(null);
    const [toast, setToast]           = useState<string | null>(null);
    const [form, setForm]             = useState({ doc_type: "contract", employee_name: "", instructions: "" });
    const [nlText, setNlText]         = useState("");
    const [nlGenerating, setNlGenerating] = useState(false);

    const showToast = (msg: string) => { setToast(msg); setTimeout(() => setToast(null), 3500); };

    const loadDocs = useCallback(async () => {
        try { setDocs(await hrDocuments.list({ limit: 50 })); } catch {}
    }, []);

    useEffect(() => { setLoading(true); loadDocs().finally(() => setLoading(false)); }, [loadDocs]);

    const handleNLGenerate = async () => {
        if (!nlText.trim()) return;
        setNlGenerating(true); setError(null);
        try {
            const parsed = parseNLIntent(nlText.trim());
            if (!parsed.employee_name) { setError("No detecté el nombre del empleado. Ej: '…para Laura Martínez'"); setNlGenerating(false); return; }
            const doc = await hrDocuments.generate({ doc_type: parsed.doc_type, employee_name: parsed.employee_name, instructions: parsed.instructions || nlText.trim() });
            setDocs(prev => [doc, ...prev]);
            setNlText("");
            showToast("Borrador generado");
        } catch (e: any) { setError(e?.message ?? "Error al generar"); }
        finally { setNlGenerating(false); }
    };

    const handleGenerate = async () => {
        if (!form.employee_name.trim()) { setError("Introduce el nombre del empleado"); return; }
        setGenerating(true); setError(null);
        try {
            const doc = await hrDocuments.generate({ doc_type: form.doc_type, employee_name: form.employee_name.trim(), instructions: form.instructions.trim() || undefined });
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

    return (
        <div className="max-w-6xl mx-auto px-4 py-8 space-y-6">
            {toast && (
                <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 bg-zinc-900 border border-zinc-700 text-white text-sm px-5 py-2.5 rounded-full shadow-lg">{toast}</div>
            )}
            <div>
                <h1 className="text-xl font-semibold text-white flex items-center gap-2">
                    <FileText className="w-6 h-6 text-violet-400" /> Gestoría Documental
                </h1>
                <p className="text-xs text-zinc-500 mt-1">Genera documentos laborales con IA. Los borradores requieren aprobación antes de usar.</p>
            </div>

            {/* Barra de lenguaje natural */}
            <div className="flex items-center gap-2 bg-[#18181b] border border-[#27272a] rounded-xl px-4 py-3">
                <Wand2 className="w-4 h-4 text-violet-400 shrink-0" />
                <input
                    value={nlText}
                    onChange={e => setNlText(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && handleNLGenerate()}
                    placeholder="Ej: quiero un contrato para Laura Martínez de contratación indefinida"
                    className="flex-1 bg-transparent text-sm text-white placeholder:text-zinc-600 focus:outline-none"
                />
                <button onClick={handleNLGenerate} disabled={!nlText.trim() || nlGenerating}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-violet-600 hover:bg-violet-500 disabled:opacity-40 text-white text-xs font-medium rounded-lg transition-colors shrink-0">
                    {nlGenerating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                    {nlGenerating ? "Generando…" : "Generar"}
                </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
                {/* Formulario */}
                <div className="lg:col-span-2">
                    <div className="bg-[#18181b] border border-[#27272a] rounded-xl p-5 space-y-4 sticky top-6">
                        <h2 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider flex items-center gap-2">
                            <Plus className="w-3.5 h-3.5" /> Generar documento
                        </h2>
                        <div className="space-y-1">
                            <label className="text-xs text-zinc-500">Tipo de documento</label>
                            <select value={form.doc_type} onChange={e => setForm(f => ({ ...f, doc_type: e.target.value }))}
                                className="w-full bg-[#09090b] border border-[#27272a] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-violet-500/50">
                                {DOC_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                            </select>
                        </div>
                        <div className="space-y-1">
                            <label className="text-xs text-zinc-500">Nombre del empleado</label>
                            <input value={form.employee_name} onChange={e => setForm(f => ({ ...f, employee_name: e.target.value }))}
                                placeholder="Ej: María López"
                                className="w-full bg-[#09090b] border border-[#27272a] rounded-lg px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-violet-500/50" />
                        </div>
                        <div className="space-y-1">
                            <label className="text-xs text-zinc-500">Instrucciones <span className="text-zinc-600">(opcional)</span></label>
                            <textarea value={form.instructions} onChange={e => setForm(f => ({ ...f, instructions: e.target.value }))}
                                placeholder="Ej: Contrato a tiempo parcial, 20h/semana…" rows={3}
                                className="w-full bg-[#09090b] border border-[#27272a] rounded-lg px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-violet-500/50 resize-none" />
                        </div>
                        {error && <p className="text-xs text-red-400">{error}</p>}
                        <div className="p-3 bg-amber-500/5 border border-amber-500/20 rounded-lg">
                            <p className="text-xs text-amber-400/80">⚠️ Borradores orientativos. Revisa y aprueba antes de cualquier uso legal.</p>
                        </div>
                        <button onClick={handleGenerate} disabled={generating || !form.employee_name.trim()}
                            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-violet-600 hover:bg-violet-500 text-white rounded-lg text-sm font-medium disabled:opacity-50 transition-colors">
                            {generating && <Loader2 className="w-4 h-4 animate-spin" />}
                            {generating ? "Generando borrador…" : "Generar borrador"}
                        </button>
                    </div>
                </div>

                {/* Lista */}
                <div className="lg:col-span-3 space-y-3">
                    <p className="text-xs font-semibold text-zinc-600 uppercase tracking-wider">Documentos ({docs.length})</p>
                    {loading ? (
                        <div className="flex justify-center py-16"><div className="w-6 h-6 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" /></div>
                    ) : docs.length === 0 ? (
                        <div className="text-center py-16 border-2 border-dashed border-[#27272a] rounded-xl">
                            <FileText className="w-8 h-8 text-zinc-700 mx-auto mb-3" />
                            <p className="text-zinc-500 text-sm">Sin documentos todavía</p>
                        </div>
                    ) : docs.map(doc => (
                        <DocumentCard key={doc.id} doc={doc} onApprove={handleApprove} onDelete={handleDelete} />
                    ))}
                </div>
            </div>
        </div>
    );
}
