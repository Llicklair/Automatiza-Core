"use client";

import { useTranslations } from "next-intl";
import type { RecruitmentPosition, Candidate } from "@/lib/api/recruitment";
import {
    Upload, Loader2, Star, CheckCircle2, XCircle, ArrowUpDown, Briefcase,
} from "lucide-react";

const STATUS_COLORS: Record<string, string> = {
    new: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    reviewed: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    shortlisted: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    rejected: "bg-red-500/10 text-red-400 border-red-500/20",
    hired: "bg-purple-500/10 text-purple-400 border-purple-500/20",
};

// I18N — config estructural + labelKey; el componente traduce en render.
const STATUS_LABEL_KEYS: Record<string, string> = {
    new: "reclutamiento.candidateStatus.new",
    reviewed: "reclutamiento.candidateStatus.reviewed",
    shortlisted: "reclutamiento.candidateStatus.shortlisted",
    rejected: "reclutamiento.candidateStatus.rejected",
    hired: "reclutamiento.candidateStatus.hired",
};

interface CandidateListProps {
    selectedPos: RecruitmentPosition | null;
    candidates: Candidate[];
    loadingCandidates: boolean;
    uploading: boolean;
    fileInputRef: React.RefObject<HTMLInputElement | null>;
    onUploadCV: (e: React.ChangeEvent<HTMLInputElement>) => void;
    onUpdateStatus: (candidateId: string, status: string) => void;
}

export function CandidateList({
    selectedPos, candidates, loadingCandidates, uploading,
    fileInputRef, onUploadCV, onUpdateStatus,
}: CandidateListProps) {
    const t = useTranslations("rrhh");
    if (!selectedPos) {
        return (
            <div className="flex flex-col items-center justify-center py-16 text-center">
                <Briefcase className="w-8 h-8 text-muted-foreground mb-3" />
                <p className="text-sm text-muted-foreground">{t("reclutamiento.candidates.selectPositionHint")}</p>
            </div>
        );
    }

    return (
        <>
            <div className="flex items-center justify-between">
                <h2 className="text-sm font-medium text-foreground">
                    {t("reclutamiento.candidates.title", { position: selectedPos.title })}
                </h2>
                <div className="flex items-center gap-2">
                    <input
                        ref={fileInputRef}
                        type="file"
                        accept=".pdf"
                        className="hidden"
                        onChange={onUploadCV}
                    />
                    <button
                        onClick={() => fileInputRef.current?.click()}
                        disabled={uploading}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-foreground text-xs font-medium transition-colors"
                    >
                        {uploading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5" />}
                        {uploading ? t("reclutamiento.candidates.analyzing") : t("reclutamiento.candidates.uploadCv")}
                    </button>
                </div>
            </div>

            {loadingCandidates ? (
                <div className="flex justify-center py-12"><Loader2 className="w-5 h-5 animate-spin text-muted-foreground" /></div>
            ) : candidates.length === 0 ? (
                <div className="flex flex-col items-center py-12 text-center">
                    <Upload className="w-8 h-8 text-muted-foreground mb-3" />
                    <p className="text-sm text-muted-foreground">{t("reclutamiento.candidates.emptyTitle")}</p>
                    <p className="text-xs text-muted-foreground mt-1">{t("reclutamiento.candidates.emptyDescription")}</p>
                </div>
            ) : (
                <div className="space-y-2">
                    {candidates.map(c => (
                        <CandidateCard key={c.id} candidate={c} onUpdateStatus={onUpdateStatus} />
                    ))}
                </div>
            )}
        </>
    );
}

interface CandidateCardProps {
    candidate: Candidate;
    onUpdateStatus: (candidateId: string, status: string) => void;
}

function CandidateCard({ candidate: c, onUpdateStatus }: CandidateCardProps) {
    const t = useTranslations("rrhh");
    return (
        <div className="bg-card border border-border rounded-xl p-4 space-y-3">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-foreground">{c.name}</span>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full border font-medium ${STATUS_COLORS[c.status] || ""}`}>
                        {STATUS_LABEL_KEYS[c.status] ? t(STATUS_LABEL_KEYS[c.status]) : c.status}
                    </span>
                </div>
                {c.score != null ? (
                    <div className="flex items-center gap-1">
                        <Star className="w-3.5 h-3.5 text-amber-400" />
                        <span className="text-sm font-bold text-amber-400">{c.score}</span>
                        <span className="text-[10px] text-muted-foreground">/100</span>
                    </div>
                ) : (
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-muted text-muted-foreground border border-border">
                        {t("reclutamiento.candidates.pendingAnalysis")}
                    </span>
                )}
            </div>

            {/* Details */}
            <div className="grid grid-cols-2 gap-2 text-xs">
                {c.email && <div className="text-muted-foreground">{t("reclutamiento.candidates.email")} <span className="text-foreground">{c.email}</span></div>}
                {c.phone && <div className="text-muted-foreground">{t("reclutamiento.candidates.phone")} <span className="text-foreground">{c.phone}</span></div>}
                {c.experience_years != null && (
                    <div className="text-muted-foreground">{t("reclutamiento.candidates.experience")} <span className="text-foreground">{t("reclutamiento.candidates.experienceYears", { n: c.experience_years })}</span></div>
                )}
                {c.education && <div className="text-muted-foreground col-span-2">{t("reclutamiento.candidates.education")} <span className="text-foreground">{c.education}</span></div>}
            </div>

            {/* Score bar */}
            {c.score != null && (
                <div className="space-y-1">
                    <div className="flex justify-between text-[10px] text-muted-foreground">
                        <span>{t("reclutamiento.candidates.aiScore")}</span>
                        <span>{c.score}/100</span>
                    </div>
                    <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                        <div
                            className={`h-full rounded-full transition-all ${c.score >= 70 ? "bg-emerald-500" : c.score >= 50 ? "bg-amber-500" : "bg-red-500"}`}
                            style={{ width: `${c.score}%` }}
                        />
                    </div>
                </div>
            )}

            {/* Languages */}
            {c.languages?.length > 0 && (
                <div className="flex flex-wrap gap-1">
                    {c.languages.map((l, i) => (
                        <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
                            {typeof l === "string" ? l : `${l.lang}${l.level ? ` (${l.level})` : ""}`}
                        </span>
                    ))}
                </div>
            )}

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
                <p className="text-xs text-muted-foreground leading-relaxed">{c.summary}</p>
            )}

            {/* Score breakdown */}
            {c.score_breakdown && Object.keys(c.score_breakdown).length > 0 && (
                <div className="flex gap-3 flex-wrap">
                    {Object.entries(c.score_breakdown).map(([key, val]) => (
                        <div key={key} className="text-[10px]">
                            <span className="text-muted-foreground">{key.replace(/_/g, " ")}: </span>
                            <span className="text-foreground font-medium">{val}</span>
                        </div>
                    ))}
                </div>
            )}

            {/* Actions */}
            <div className="flex gap-1.5 pt-1">
                {c.status !== "shortlisted" && c.status !== "hired" && (
                    <button
                        onClick={() => onUpdateStatus(c.id, "shortlisted")}
                        className="flex items-center gap-1 px-2 py-1 rounded-md bg-emerald-600/10 text-emerald-400 text-[10px] font-medium hover:bg-emerald-600/20 transition-colors"
                    >
                        <CheckCircle2 className="w-3 h-3" /> {t("reclutamiento.candidates.shortlist")}
                    </button>
                )}
                {c.status !== "rejected" && c.status !== "hired" && (
                    <button
                        onClick={() => onUpdateStatus(c.id, "rejected")}
                        className="flex items-center gap-1 px-2 py-1 rounded-md bg-red-600/10 text-red-400 text-[10px] font-medium hover:bg-red-600/20 transition-colors"
                    >
                        <XCircle className="w-3 h-3" /> {t("reclutamiento.candidates.reject")}
                    </button>
                )}
                {c.status === "shortlisted" && (
                    <button
                        onClick={() => onUpdateStatus(c.id, "hired")}
                        className="flex items-center gap-1 px-2 py-1 rounded-md bg-purple-600/10 text-purple-400 text-[10px] font-medium hover:bg-purple-600/20 transition-colors"
                    >
                        <CheckCircle2 className="w-3 h-3" /> {t("reclutamiento.candidates.hire")}
                    </button>
                )}
                {c.status !== "reviewed" && c.status !== "shortlisted" && c.status !== "hired" && (
                    <button
                        onClick={() => onUpdateStatus(c.id, "reviewed")}
                        className="flex items-center gap-1 px-2 py-1 rounded-md bg-accent text-muted-foreground text-[10px] font-medium hover:bg-accent transition-colors"
                    >
                        <ArrowUpDown className="w-3 h-3" /> {t("reclutamiento.candidates.markReviewed")}
                    </button>
                )}
            </div>
        </div>
    );
}
