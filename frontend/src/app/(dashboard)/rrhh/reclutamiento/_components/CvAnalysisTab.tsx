"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
    Upload, Loader2, Mail, Phone, GraduationCap, Briefcase, Globe, Star, UserPlus,
} from "lucide-react";
import { api } from "@/lib/api";
import type { RecruitmentPosition } from "@/lib/api/recruitment";
import { useToastStore } from "@/stores/toast";
import { Button } from "@/components/ui/button";
import { useAnalisisCV } from "../_hooks/useAnalisisCV";

export function CvAnalysisTab({
    positions,
    onCandidateCreated,
}: {
    positions: RecruitmentPosition[];
    onCandidateCreated: (positionId: string) => void;
}) {
    const t = useTranslations("rrhh");
    const {
        fileRef, dragging, setDragging, analyzing, result, error, fileName, file,
        handleFileChange, handleDrop, triggerFileInput, reset,
    } = useAnalisisCV();
    const showToast = useToastStore((s) => s.show);

    const [posId, setPosId] = useState("");
    const [creating, setCreating] = useState(false);

    const createCandidate = async () => {
        if (!posId || !file) return;
        setCreating(true);
        try {
            await api.recruitment.uploadCV(posId, file);
            showToast(t("toasts.candidateCreated"), "success");
            reset();
            setPosId("");
            onCandidateCreated(posId);
        } catch (e: any) {
            showToast(e?.message ?? t("toasts.candidateCreateError"), "error");
        } finally {
            setCreating(false);
        }
    };

    return (
        <div className="space-y-6">
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
                        <p className="text-sm text-muted-foreground">
                            {t.rich("analisisCv.analyzingFile", {
                                name: () => <span className="text-violet-400">{fileName}</span>,
                            })}
                        </p>
                        <p className="text-xs text-muted-foreground">{t("analisisCv.extractingInfo")}</p>
                    </div>
                ) : (
                    <div className="flex flex-col items-center gap-3">
                        <Upload className="w-10 h-10 text-muted-foreground" />
                        <p className="text-sm text-muted-foreground">
                            {t.rich("analisisCv.dropHint", {
                                b: (chunks) => <span className="text-violet-400">{chunks}</span>,
                            })}
                        </p>
                        <p className="text-xs text-muted-foreground">{t("analisisCv.fileConstraints")}</p>
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
                                <h2 className="text-xl font-bold text-foreground">{result.name ?? t("analisisCv.nameNotDetected")}</h2>
                                <div className="flex flex-wrap items-center gap-3 mt-2">
                                    {result.email && <span className="flex items-center gap-1 text-sm text-muted-foreground"><Mail className="w-4 h-4 text-muted-foreground" />{result.email}</span>}
                                    {result.phone && <span className="flex items-center gap-1 text-sm text-muted-foreground"><Phone className="w-4 h-4 text-muted-foreground" />{result.phone}</span>}
                                </div>
                            </div>
                            {result.experience_years != null && (
                                <div className="flex flex-col items-center bg-violet-500/10 border border-violet-500/20 rounded-xl px-4 py-3 shrink-0">
                                    <span className="text-2xl font-bold text-violet-400">{result.experience_years}</span>
                                    <span className="text-xs text-muted-foreground">{t("analisisCv.yearsExp")}</span>
                                </div>
                            )}
                        </div>
                    </div>

                    <div className="p-6 space-y-5">
                        {result.summary && (
                            <div className="space-y-1.5">
                                <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5"><Star className="w-3.5 h-3.5" /> {t("analisisCv.aiSummary")}</h3>
                                <p className="text-sm text-foreground leading-relaxed">{result.summary}</p>
                            </div>
                        )}
                        {result.education && (
                            <div className="space-y-1.5">
                                <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5"><GraduationCap className="w-3.5 h-3.5" /> {t("analisisCv.education")}</h3>
                                <p className="text-sm text-muted-foreground">{result.education}</p>
                            </div>
                        )}
                        {result.skills?.length > 0 && (
                            <div className="space-y-1.5">
                                <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5"><Briefcase className="w-3.5 h-3.5" /> {t("analisisCv.skills", { n: result.skills.length })}</h3>
                                <div className="flex flex-wrap gap-1.5">
                                    {result.skills.map((s, i) => (
                                        <span key={i} className="px-2.5 py-1 rounded-full bg-violet-500/10 text-violet-400 text-xs font-medium border border-violet-500/20">{s}</span>
                                    ))}
                                </div>
                            </div>
                        )}
                        {result.languages?.length > 0 && (
                            <div className="space-y-1.5">
                                <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5"><Globe className="w-3.5 h-3.5" /> {t("analisisCv.languages")}</h3>
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

                    {/* Flujo conectado: convertir el análisis en un candidato de una vacante */}
                    <div className="border-t border-border bg-muted/30 px-6 py-4">
                        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5 mb-3">
                            <UserPlus className="w-3.5 h-3.5" /> {t("analisisCv.addAsCandidate")}
                        </h3>
                        {positions.length === 0 ? (
                            <p className="text-sm text-muted-foreground">
                                {t("analisisCv.createPositionFirst")}
                            </p>
                        ) : (
                            <div className="flex flex-wrap items-center gap-3">
                                <select
                                    value={posId}
                                    onChange={e => setPosId(e.target.value)}
                                    className="bg-card border border-border rounded-lg px-3 py-2 text-sm text-foreground min-w-[220px]"
                                >
                                    <option value="">{t("analisisCv.selectPosition")}</option>
                                    {positions.map(p => (
                                        <option key={p.id} value={p.id}>{p.title}</option>
                                    ))}
                                </select>
                                <Button onClick={createCandidate} disabled={!posId || creating}>
                                    {creating ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <UserPlus className="w-4 h-4 mr-2" />}
                                    {t("analisisCv.createCandidate")}
                                </Button>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
