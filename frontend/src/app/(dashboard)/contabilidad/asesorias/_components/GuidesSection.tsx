"use client";

import { BookOpen, ChevronDown, ChevronUp, ExternalLink, Gavel, Lightbulb } from "lucide-react";

interface GuidesSectionProps {
    guides: any[];
    filter: string;
    expandedGuide: number | null;
    setExpandedGuide: (i: number | null) => void;
}

export function GuidesSection({ guides, filter, expandedGuide, setExpandedGuide }: GuidesSectionProps) {
    return (
        <div className="space-y-4">
            <div className="flex items-center gap-2">
                <BookOpen className="w-5 h-5 text-muted-foreground" />
                <h2 className="text-xl font-semibold text-foreground">
                    Guía Normativa — {filter === "fiscal" ? "Fiscal / AEAT" : filter === "laboral" ? "Laboral" : "Mercantil"}
                </h2>
            </div>

            <div className="grid gap-3">
                {guides.map((guide: any, i: number) => {
                    const isExpanded = expandedGuide === i;
                    return (
                        <div
                            key={i}
                            className="bg-card border border-border rounded-2xl overflow-hidden shadow-lg shadow-black/10 transition-all"
                        >
                            <button
                                onClick={() => setExpandedGuide(isExpanded ? null : i)}
                                className="w-full p-5 flex items-start gap-4 text-left hover:bg-accent/50 transition-colors"
                            >
                                <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                                    <Gavel className="w-5 h-5 text-primary" />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <h3 className="text-foreground font-medium leading-snug">{guide.titulo}</h3>
                                    <p className="text-muted-foreground text-sm mt-1 line-clamp-2">{guide.resumen}</p>
                                </div>
                                <div className="flex-shrink-0 mt-1">
                                    {isExpanded
                                        ? <ChevronUp className="w-5 h-5 text-muted-foreground" />
                                        : <ChevronDown className="w-5 h-5 text-muted-foreground" />
                                    }
                                </div>
                            </button>

                            {isExpanded && (
                                <div className="px-5 pb-5 pt-0 space-y-4 border-t border-border animate-in fade-in slide-in-from-top-2 duration-200">
                                    <div className="pt-4">
                                        <p className="text-foreground text-sm leading-relaxed">{guide.resumen}</p>
                                    </div>

                                    <div className="flex items-start gap-3 bg-card rounded-xl p-4 border border-border">
                                        <Lightbulb className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
                                        <div>
                                            <p className="text-xs font-semibold text-amber-400 uppercase tracking-wider mb-1">Consejo para tu PYME</p>
                                            <p className="text-foreground text-sm leading-relaxed">{guide.consejo_pyme}</p>
                                        </div>
                                    </div>

                                    <div className="flex flex-col sm:flex-row sm:items-center gap-3 text-xs">
                                        <span className="text-muted-foreground bg-card px-3 py-1.5 rounded-lg border border-border font-mono">
                                            {guide.referencia_legal}
                                        </span>
                                        {guide.url_boe && (
                                            <a
                                                href={guide.url_boe}
                                                target="_blank"
                                                rel="noreferrer"
                                                className="flex items-center gap-1.5 text-primary hover:text-primary transition-colors"
                                            >
                                                <ExternalLink className="w-3.5 h-3.5" />
                                                Ver en el BOE
                                            </a>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
