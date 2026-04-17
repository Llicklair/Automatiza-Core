"use client";

import type { RecruitmentPosition } from "@/lib/api/recruitment";
import { Loader2, Users, ChevronRight } from "lucide-react";

interface PositionListProps {
    positions: RecruitmentPosition[];
    selectedPos: RecruitmentPosition | null;
    loading: boolean;
    onSelect: (pos: RecruitmentPosition) => void;
}

export function PositionList({ positions, selectedPos, loading, onSelect }: PositionListProps) {
    return (
        <div className="space-y-2">
            <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider px-1">Puestos</h2>
            {loading ? (
                <div className="flex justify-center py-8"><Loader2 className="w-5 h-5 animate-spin text-muted-foreground" /></div>
            ) : positions.length === 0 ? (
                <div className="text-center py-8 text-xs text-muted-foreground">Sin puestos. Crea el primero.</div>
            ) : positions.map(pos => (
                <button
                    key={pos.id}
                    onClick={() => onSelect(pos)}
                    className={`w-full text-left p-3 rounded-xl border transition-colors ${
                        selectedPos?.id === pos.id
                            ? "bg-violet-600/10 border-violet-500/30"
                            : "bg-card border-border hover:border-border"
                    }`}
                >
                    <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-foreground">{pos.title}</span>
                        <ChevronRight className="w-3.5 h-3.5 text-muted-foreground" />
                    </div>
                    <div className="flex items-center gap-2 mt-1">
                        {pos.department && <span className="text-[10px] text-muted-foreground">{pos.department}</span>}
                        <span className="text-[10px] text-muted-foreground">|</span>
                        <span className="text-[10px] text-violet-400 flex items-center gap-1">
                            <Users className="w-3 h-3" /> {pos.candidate_count}
                        </span>
                    </div>
                    {pos.required_skills?.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-2">
                            {pos.required_skills.slice(0, 4).map((s, i) => (
                                <span key={i} className="text-[9px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">{s}</span>
                            ))}
                            {pos.required_skills.length > 4 && (
                                <span className="text-[9px] text-muted-foreground">+{pos.required_skills.length - 4}</span>
                            )}
                        </div>
                    )}
                </button>
            ))}
        </div>
    );
}
