"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { RecruitmentPosition, Candidate } from "@/lib/api/recruitment";
import {
    Briefcase, Plus, Upload, Loader2, Users, Star, ChevronRight,
    X, CheckCircle2, XCircle, ArrowUpDown,
} from "lucide-react";

const STATUS_COLORS: Record<string, string> = {
    new: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    reviewed: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    shortlisted: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    rejected: "bg-red-500/10 text-red-400 border-red-500/20",
    hired: "bg-purple-500/10 text-purple-400 border-purple-500/20",
};

const STATUS_LABELS: Record<string, string> = {
    new: "Nuevo", reviewed: "Revisado", shortlisted: "Preseleccionado",
    rejected: "Descartado", hired: "Contratado",
};

export default function RecruitmentPage() {
    const [positions, setPositions] = useState<RecruitmentPosition[]>([]);
    const [selectedPos, setSelectedPos] = useState<RecruitmentPosition | null>(null);
    const [candidates, setCandidates] = useState<Candidate[]>([]);
    const [loading, setLoading] = useState(true);
    const [loadingCandidates, setLoadingCandidates] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Form state
    const [form, setForm] = useState({ title: "", department: "", description: "", required_skills: "", experience_min_years: 0 });

    const loadPositions = async () => {
        try {
            const data = await api.recruitment.listPositions();
            setPositions(data);
        } catch { /* silent */ }
        setLoading(false);
    };

    const loadCandidates = async (posId: string) => {
        setLoadingCandidates(true);
        try {
            const data = await api.recruitment.listCandidates(posId);
            setCandidates(data);
        } catch { setCandidates([]); }
        setLoadingCandidates(false);
    };

    useEffect(() => { loadPositions(); }, []);

    const selectPosition = (pos: RecruitmentPosition) => {
        setSelectedPos(pos);
        loadCandidates(pos.id);
    };

    const createPosition = async () => {
        const skills = form.required_skills.split(",").map(s => s.trim()).filter(Boolean);
        await api.recruitment.createPosition({
            title: form.title, department: form.department, description: form.description,
            required_skills: skills, experience_min_years: form.experience_min_years,
        });
        setShowCreateModal(false);
        setForm({ title: "", department: "", description: "", required_skills: "", experience_min_years: 0 });
        loadPositions();
    };

    const handleUploadCV = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (!selectedPos || !e.target.files?.length) return;
        setUploading(true);
        try {
            await api.recruitment.uploadCV(selectedPos.id, e.target.files[0]);
            loadCandidates(selectedPos.id);
            loadPositions(); // refresh counts
        } catch (err: any) {
            alert(err?.message || "Error subiendo CV");
        }
        setUploading(false);
        if (fileInputRef.current) fileInputRef.current.value = "";
    };

    const updateStatus = async (candidateId: string, status: string) => {
        await api.recruitment.updateCandidateStatus(candidateId, status);
        if (selectedPos) loadCandidates(selectedPos.id);
    };

    return (
        <div className="p-6 max-w-6xl mx-auto space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="p-2.5 rounded-xl bg-violet-500/10 border border-violet-500/20">
                        <Briefcase className="w-5 h-5 text-violet-400" />
                    </div>
                    <div>
                        <h1 className="text-lg font-semibold text-white">Reclutamiento</h1>
                        <p className="text-xs text-zinc-500">Gestiona puestos abiertos y analiza CVs con IA</p>
                    </div>
                </div>
                <button
                    onClick={() => setShowCreateModal(true)}
                    className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-violet-600 hover:bg-violet-500 text-white text-xs font-medium transition-colors"
                >
                    <Plus className="w-3.5 h-3.5" /> Nuevo puesto
                </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                {/* Positions list */}
                <div className="space-y-2">
                    <h2 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider px-1">Puestos</h2>
                    {loading ? (
                        <div className="flex justify-center py-8"><Loader2 className="w-5 h-5 animate-spin text-zinc-500" /></div>
                    ) : positions.length === 0 ? (
                        <div className="text-center py-8 text-xs text-zinc-600">Sin puestos. Crea el primero.</div>
                    ) : positions.map(pos => (
                        <button
                            key={pos.id}
                            onClick={() => selectPosition(pos)}
                            className={`w-full text-left p-3 rounded-xl border transition-colors ${
                                selectedPos?.id === pos.id
                                    ? "bg-violet-600/10 border-violet-500/30"
                                    : "bg-[#18181b] border-[#27272a] hover:border-zinc-600"
                            }`}
                        >
                            <div className="flex items-center justify-between">
                                <span className="text-sm font-medium text-white">{pos.title}</span>
                                <ChevronRight className="w-3.5 h-3.5 text-zinc-600" />
                            </div>
                            <div className="flex items-center gap-2 mt-1">
                                {pos.department && <span className="text-[10px] text-zinc-500">{pos.department}</span>}
                                <span className="text-[10px] text-zinc-600">|</span>
                                <span className="text-[10px] text-violet-400 flex items-center gap-1">
                                    <Users className="w-3 h-3" /> {pos.candidate_count}
                                </span>
                            </div>
                            {pos.required_skills?.length > 0 && (
                                <div className="flex flex-wrap gap-1 mt-2">
                                    {pos.required_skills.slice(0, 4).map((s, i) => (
                                        <span key={i} className="text-[9px] px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400">{s}</span>
                                    ))}
                                    {pos.required_skills.length > 4 && (
                                        <span className="text-[9px] text-zinc-600">+{pos.required_skills.length - 4}</span>
                                    )}
                                </div>
                            )}
                        </button>
                    ))}
                </div>

                {/* Candidates */}
                <div className="lg:col-span-2 space-y-3">
                    {selectedPos ? (
                        <>
                            <div className="flex items-center justify-between">
                                <h2 className="text-sm font-medium text-white">
                                    Candidatos — {selectedPos.title}
                                </h2>
                                <div className="flex items-center gap-2">
                                    <input
                                        ref={fileInputRef}
                                        type="file"
                                        accept=".pdf"
                                        className="hidden"
                                        onChange={handleUploadCV}
                                    />
                                    <button
                                        onClick={() => fileInputRef.current?.click()}
                                        disabled={uploading}
                                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-medium transition-colors"
                                    >
                                        {uploading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5" />}
                                        {uploading ? "Analizando..." : "Subir CV"}
                                    </button>
                                </div>
                            </div>

                            {loadingCandidates ? (
                                <div className="flex justify-center py-12"><Loader2 className="w-5 h-5 animate-spin text-zinc-500" /></div>
                            ) : candidates.length === 0 ? (
                                <div className="flex flex-col items-center py-12 text-center">
                                    <Upload className="w-8 h-8 text-zinc-700 mb-3" />
                                    <p className="text-sm text-zinc-500">Sin candidatos</p>
                                    <p className="text-xs text-zinc-600 mt-1">Sube un CV en PDF para que la IA lo analice y puntúe</p>
                                </div>
                            ) : (
                                <div className="space-y-2">
                                    {candidates.map(c => (
                                        <div key={c.id} className="bg-[#18181b] border border-[#27272a] rounded-xl p-4 space-y-3">
                                            {/* Header */}
                                            <div className="flex items-center justify-between">
                                                <div className="flex items-center gap-2">
                                                    <span className="text-sm font-medium text-white">{c.name}</span>
                                                    <span className={`text-[10px] px-2 py-0.5 rounded-full border font-medium ${STATUS_COLORS[c.status] || ""}`}>
                                                        {STATUS_LABELS[c.status] || c.status}
                                                    </span>
                                                </div>
                                                {c.score != null && (
                                                    <div className="flex items-center gap-1">
                                                        <Star className="w-3.5 h-3.5 text-amber-400" />
                                                        <span className="text-sm font-bold text-amber-400">{c.score}</span>
                                                        <span className="text-[10px] text-zinc-600">/100</span>
                                                    </div>
                                                )}
                                            </div>

                                            {/* Details */}
                                            <div className="grid grid-cols-2 gap-2 text-xs">
                                                {c.email && <div className="text-zinc-500">Email: <span className="text-zinc-300">{c.email}</span></div>}
                                                {c.phone && <div className="text-zinc-500">Tel: <span className="text-zinc-300">{c.phone}</span></div>}
                                                {c.experience_years != null && (
                                                    <div className="text-zinc-500">Experiencia: <span className="text-zinc-300">{c.experience_years} años</span></div>
                                                )}
                                                {c.education && <div className="text-zinc-500 col-span-2">Formación: <span className="text-zinc-300">{c.education}</span></div>}
                                            </div>

                                            {/* Skills */}
                                            {c.skills?.length > 0 && (
                                                <div className="flex flex-wrap gap-1">
                                                    {c.skills.map((s, i) => (
                                                        <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-violet-500/10 text-violet-400 border border-violet-500/20">{s}</span>
                                                    ))}
                                                </div>
                                            )}

                                            {/* Summary */}
                                            {c.summary && (
                                                <p className="text-xs text-zinc-400 leading-relaxed">{c.summary}</p>
                                            )}

                                            {/* Score breakdown */}
                                            {c.score_breakdown && Object.keys(c.score_breakdown).length > 0 && (
                                                <div className="flex gap-3 flex-wrap">
                                                    {Object.entries(c.score_breakdown).map(([key, val]) => (
                                                        <div key={key} className="text-[10px]">
                                                            <span className="text-zinc-600">{key.replace(/_/g, " ")}: </span>
                                                            <span className="text-zinc-300 font-medium">{val}</span>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}

                                            {/* Actions */}
                                            <div className="flex gap-1.5 pt-1">
                                                {c.status !== "shortlisted" && c.status !== "hired" && (
                                                    <button
                                                        onClick={() => updateStatus(c.id, "shortlisted")}
                                                        className="flex items-center gap-1 px-2 py-1 rounded-md bg-emerald-600/10 text-emerald-400 text-[10px] font-medium hover:bg-emerald-600/20 transition-colors"
                                                    >
                                                        <CheckCircle2 className="w-3 h-3" /> Preseleccionar
                                                    </button>
                                                )}
                                                {c.status !== "rejected" && c.status !== "hired" && (
                                                    <button
                                                        onClick={() => updateStatus(c.id, "rejected")}
                                                        className="flex items-center gap-1 px-2 py-1 rounded-md bg-red-600/10 text-red-400 text-[10px] font-medium hover:bg-red-600/20 transition-colors"
                                                    >
                                                        <XCircle className="w-3 h-3" /> Descartar
                                                    </button>
                                                )}
                                                {c.status === "shortlisted" && (
                                                    <button
                                                        onClick={() => updateStatus(c.id, "hired")}
                                                        className="flex items-center gap-1 px-2 py-1 rounded-md bg-purple-600/10 text-purple-400 text-[10px] font-medium hover:bg-purple-600/20 transition-colors"
                                                    >
                                                        <CheckCircle2 className="w-3 h-3" /> Contratar
                                                    </button>
                                                )}
                                                {c.status !== "reviewed" && c.status !== "shortlisted" && c.status !== "hired" && (
                                                    <button
                                                        onClick={() => updateStatus(c.id, "reviewed")}
                                                        className="flex items-center gap-1 px-2 py-1 rounded-md bg-zinc-700/30 text-zinc-400 text-[10px] font-medium hover:bg-zinc-700/50 transition-colors"
                                                    >
                                                        <ArrowUpDown className="w-3 h-3" /> Marcar revisado
                                                    </button>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </>
                    ) : (
                        <div className="flex flex-col items-center justify-center py-16 text-center">
                            <Briefcase className="w-8 h-8 text-zinc-700 mb-3" />
                            <p className="text-sm text-zinc-500">Selecciona un puesto para ver sus candidatos</p>
                        </div>
                    )}
                </div>
            </div>

            {/* Create position modal */}
            {showCreateModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
                    <div className="bg-[#18181b] border border-[#27272a] rounded-2xl p-6 w-full max-w-md space-y-4">
                        <div className="flex items-center justify-between">
                            <h3 className="text-sm font-semibold text-white">Nuevo puesto</h3>
                            <button onClick={() => setShowCreateModal(false)}><X className="w-4 h-4 text-zinc-500" /></button>
                        </div>
                        <div className="space-y-3">
                            <input
                                placeholder="Título del puesto *"
                                value={form.title}
                                onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                                className="w-full bg-[#09090b] border border-[#27272a] rounded-lg px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-violet-500/50"
                            />
                            <input
                                placeholder="Departamento"
                                value={form.department}
                                onChange={e => setForm(f => ({ ...f, department: e.target.value }))}
                                className="w-full bg-[#09090b] border border-[#27272a] rounded-lg px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-violet-500/50"
                            />
                            <textarea
                                placeholder="Descripción del puesto"
                                value={form.description}
                                onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                                rows={3}
                                className="w-full bg-[#09090b] border border-[#27272a] rounded-lg px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-violet-500/50 resize-none"
                            />
                            <input
                                placeholder="Habilidades requeridas (separadas por coma)"
                                value={form.required_skills}
                                onChange={e => setForm(f => ({ ...f, required_skills: e.target.value }))}
                                className="w-full bg-[#09090b] border border-[#27272a] rounded-lg px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-violet-500/50"
                            />
                            <div className="flex items-center gap-2">
                                <label className="text-xs text-zinc-500 whitespace-nowrap">Exp. mínima (años):</label>
                                <input
                                    type="number"
                                    min={0}
                                    step={0.5}
                                    value={form.experience_min_years}
                                    onChange={e => setForm(f => ({ ...f, experience_min_years: parseFloat(e.target.value) || 0 }))}
                                    className="w-20 bg-[#09090b] border border-[#27272a] rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-violet-500/50"
                                />
                            </div>
                        </div>
                        <div className="flex justify-end gap-2 pt-2">
                            <button
                                onClick={() => setShowCreateModal(false)}
                                className="px-3 py-1.5 rounded-lg text-xs text-zinc-400 hover:text-white transition-colors"
                            >
                                Cancelar
                            </button>
                            <button
                                onClick={createPosition}
                                disabled={!form.title.trim()}
                                className="px-4 py-1.5 rounded-lg bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white text-xs font-medium transition-colors"
                            >
                                Crear puesto
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
