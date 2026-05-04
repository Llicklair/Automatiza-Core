"use client";

import { useAnalisisCV } from "./_hooks/useAnalisisCV";
import { FileSearch, Upload, Loader2, Mail, Phone, GraduationCap, Briefcase, Globe, Star } from "lucide-react";
import { PageHeader } from "@/components/shared/PageHeader";

export default function AnalisisCVPage() {
    const {
        fileRef,
        dragging, setDragging,
        analyzing,
        result,
        error,
        fileName,
        handleFileChange,
        handleDrop,
        triggerFileInput,
    } = useAnalisisCV();

    return (
        <div className="p-8 max-w-[1400px] mx-auto space-y-6">
            <PageHeader
                title="Análisis de CV con IA"
                description="Sube un CV en PDF y la IA extrae automáticamente toda la información relevante."
                icon={FileSearch}
            />

            {/* Drop zone */}
            <div
                onDragOver={e => { e.preventDefault(); setDragging(true); }}
                onDragLeave={() => setDragging(false)}
                onDrop={handleDrop}
                onClick={triggerFileInput}
                className={`relative cursor-pointer border-2 border-dashed rounded-xl p-10 text-center transition-colors ${
                    dragging ? "border-violet-500/50 bg-violet-500/5" : "border-border hover:border-border hover:bg-card"
                }`}>
                <input ref={fileRef} type="file" accept=".pdf" className="hidden" onChange={handleFileChange} />
                {analyzing ? (
                    <div className="flex flex-col items-center gap-3">
                        <Loader2 className="w-10 h-10 text-violet-400 animate-spin" />
                        <p className="text-sm text-muted-foreground">Analizando <span className="text-violet-400">{fileName}</span>…</p>
                        <p className="text-xs text-muted-foreground">La IA está extrayendo la información</p>
                    </div>
                ) : (
                    <div className="flex flex-col items-center gap-3">
                        <Upload className="w-10 h-10 text-muted-foreground" />
                        <p className="text-sm text-muted-foreground">
                            Arrastra un CV aquí o <span className="text-violet-400">haz clic para seleccionar</span>
                        </p>
                        <p className="text-xs text-muted-foreground">Solo PDF · Máximo 10MB</p>
                    </div>
                )}
            </div>

            {error && <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-400">{error}</div>}

            {result && (
                <div className="bg-card border border-border rounded-xl overflow-hidden">
                    {/* Cabecera */}
                    <div className="bg-violet-500/5 border-b border-violet-500/10 px-6 py-5">
                        <div className="flex items-start justify-between gap-4">
                            <div>
                                <h2 className="text-xl font-bold text-foreground">{result.name ?? "Nombre no detectado"}</h2>
                                <div className="flex flex-wrap items-center gap-3 mt-2">
                                    {result.email && <span className="flex items-center gap-1 text-sm text-muted-foreground"><Mail className="w-4 h-4 text-muted-foreground" />{result.email}</span>}
                                    {result.phone && <span className="flex items-center gap-1 text-sm text-muted-foreground"><Phone className="w-4 h-4 text-muted-foreground" />{result.phone}</span>}
                                </div>
                            </div>
                            {result.experience_years != null && (
                                <div className="flex flex-col items-center bg-violet-500/10 border border-violet-500/20 rounded-xl px-4 py-3 shrink-0">
                                    <span className="text-2xl font-bold text-violet-400">{result.experience_years}</span>
                                    <span className="text-xs text-muted-foreground">años exp.</span>
                                </div>
                            )}
                        </div>
                    </div>

                    <div className="p-6 space-y-5">
                        {result.summary && (
                            <div className="space-y-1.5">
                                <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5"><Star className="w-3.5 h-3.5" /> Resumen IA</h3>
                                <p className="text-sm text-foreground leading-relaxed">{result.summary}</p>
                            </div>
                        )}
                        {result.education && (
                            <div className="space-y-1.5">
                                <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5"><GraduationCap className="w-3.5 h-3.5" /> Formación</h3>
                                <p className="text-sm text-muted-foreground">{result.education}</p>
                            </div>
                        )}
                        {result.skills?.length > 0 && (
                            <div className="space-y-1.5">
                                <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5"><Briefcase className="w-3.5 h-3.5" /> Habilidades ({result.skills.length})</h3>
                                <div className="flex flex-wrap gap-1.5">
                                    {result.skills.map((s, i) => (
                                        <span key={i} className="px-2.5 py-1 rounded-full bg-violet-500/10 text-violet-400 text-xs font-medium border border-violet-500/20">{s}</span>
                                    ))}
                                </div>
                            </div>
                        )}
                        {result.languages?.length > 0 && (
                            <div className="space-y-1.5">
                                <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5"><Globe className="w-3.5 h-3.5" /> Idiomas</h3>
                                <div className="flex flex-wrap gap-1.5">
                                    {result.languages.map((l, i) => (
                                        <span key={i} className="px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 text-xs font-medium border border-emerald-500/20">
                                            🌐 {typeof l === "string" ? l : `${l.lang}${l.level ? ` (${l.level})` : ""}`}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
