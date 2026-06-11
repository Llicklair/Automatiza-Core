"use client";

import { FileText, Plus, Loader2, Send, Wand2 } from "lucide-react";
import { useHRDocumentos, DOC_TYPES, DOC_TEMPLATES } from "./_hooks/useHRDocumentos";
import { DocumentCard } from "./_components/DocumentCard";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { PageContainer } from "@/components/shared/PageContainer";

export default function HRDocumentosPage() {
    const {
        docs, loading, generating, error, toast,
        form, setForm,
        nlText, setNlText, nlGenerating,
        handleNLGenerate, handleGenerate, handleApprove, handleDelete,
    } = useHRDocumentos();

    return (
        <PageContainer>
            {toast && (
                <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 bg-card border border-border text-foreground text-sm px-5 py-2.5 rounded-full shadow-lg">{toast}</div>
            )}
            <PageHeader
                title="Gestoría Documental"
                description="Genera documentos laborales con IA. Los borradores requieren aprobación antes de usar."
                icon={FileText}
            />

            <div className="flex items-center gap-2 bg-card border border-border rounded-xl px-4 py-3">
                <Wand2 className="w-4 h-4 text-violet-400 shrink-0" />
                <input
                    value={nlText}
                    onChange={e => setNlText(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && handleNLGenerate()}
                    placeholder="Ej: quiero un contrato para Laura Martínez de contratación indefinida"
                    className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
                />
                <Button size="sm" onClick={handleNLGenerate} disabled={!nlText.trim() || nlGenerating}>
                    {nlGenerating ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1.5" /> : <Send className="w-3.5 h-3.5 mr-1.5" />}
                    {nlGenerating ? "Generando…" : "Generar"}
                </Button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
                <div className="lg:col-span-2">
                    <div className="bg-card border border-border rounded-xl p-5 space-y-4 sticky top-6">
                        <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                            <Plus className="w-3.5 h-3.5" /> Generar documento
                        </h2>
                        <div className="space-y-1">
                            <label className="text-xs text-muted-foreground">Tipo de documento</label>
                            <Select
                                value={form.doc_type}
                                onValueChange={v => setForm(f => ({ ...f, doc_type: v, instructions: DOC_TEMPLATES[v] ?? "" }))}
                            >
                                <SelectTrigger className="w-full">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {DOC_TYPES.map(t => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="space-y-1">
                            <label className="text-xs text-muted-foreground">Nombre del empleado</label>
                            <Input
                                value={form.employee_name}
                                onChange={e => setForm(f => ({ ...f, employee_name: e.target.value }))}
                                placeholder="Ej: María López"
                            />
                        </div>
                        <div className="space-y-1">
                            <label className="text-xs text-muted-foreground">Instrucciones <span className="text-muted-foreground/60">(edita los corchetes con los datos reales)</span></label>
                            <textarea value={form.instructions} onChange={e => setForm(f => ({ ...f, instructions: e.target.value }))}
                                placeholder="Describe los detalles del documento…" rows={7}
                                className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-violet-500/50 resize-none" />
                        </div>
                        {error && <p className="text-xs text-red-400">{error}</p>}
                        <div className="p-3 bg-amber-500/5 border border-amber-500/20 rounded-lg">
                            <p className="text-xs text-amber-400/80">⚠️ Borradores orientativos. Revisa y aprueba antes de cualquier uso legal.</p>
                        </div>
                        <Button className="w-full" onClick={handleGenerate} disabled={generating}>
                            {generating && <Loader2 className="w-4 h-4 animate-spin mr-2" />}
                            {generating ? "Generando borrador…" : "Generar borrador"}
                        </Button>
                    </div>
                </div>

                <div className="lg:col-span-3 space-y-3">
                    <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Documentos ({docs.length})</p>
                    {loading ? (
                        <div className="flex justify-center py-16"><div className="w-6 h-6 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" /></div>
                    ) : docs.length === 0 ? (
                        <div className="text-center py-16 border-2 border-dashed border-border rounded-xl">
                            <FileText className="w-8 h-8 text-muted-foreground mx-auto mb-3" />
                            <p className="text-muted-foreground text-sm">Sin documentos todavía</p>
                        </div>
                    ) : docs.map(doc => (
                        <DocumentCard key={doc.id} doc={doc} onApprove={handleApprove} onDelete={handleDelete} />
                    ))}
                </div>
            </div>
        </PageContainer>
    );
}
