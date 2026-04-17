"use client";

import { CheckCircle2, Zap } from "lucide-react";
import Link from "next/link";
import type { Approval } from "@/lib/api";

interface ApprovalsSectionProps {
    loading: boolean;
    approvals: Approval[];
}

export function ApprovalsSection({ loading, approvals }: ApprovalsSectionProps) {
    return (
        <div className="bg-card border border-amber-500/20 rounded-2xl overflow-hidden shadow-lg shadow-amber-500/5">
            <div className="px-5 py-4 border-b border-amber-500/10 bg-gradient-to-r from-amber-500/10 to-transparent flex items-center gap-2">
                <Zap className="w-4 h-4 text-amber-500" />
                <h2 className="text-sm font-semibold text-amber-500">Aprobaciones Requeridas</h2>
                {approvals.length > 0 && (
                    <span className="ml-auto bg-amber-500 text-black text-[10px] font-bold px-2 py-0.5 rounded-full">
                        {approvals.length}
                    </span>
                )}
            </div>
            <div className="divide-y divide-border max-h-[250px] overflow-y-auto">
                {loading ? (
                    <div className="p-6 text-center text-muted-foreground text-xs text-amber-500/50">Buscando...</div>
                ) : approvals.length === 0 ? (
                    <div className="p-8 text-center text-muted-foreground text-xs flex flex-col items-center gap-2">
                        <CheckCircle2 className="w-8 h-8 text-muted-foreground" />
                        Todo al d\u00EDa. No hay cuellos de botella.
                    </div>
                ) : (
                    approvals.map(a => (
                        <div key={a.id} className="p-4 hover:bg-amber-500/5 transition-colors group cursor-default">
                            <p className="text-sm text-foreground line-clamp-2 leading-snug">{a.action_description}</p>
                            <div className="flex items-center justify-between mt-3">
                                <span className="text-[10px] uppercase font-bold text-amber-600 tracking-wider">
                                    Nivel: {a.risk_level}
                                </span>
                                <Link href="/bandeja?tab=aprobaciones" className="text-xs text-amber-500 hover:text-amber-400 font-medium opacity-0 group-hover:opacity-100 transition-opacity">
                                    Revisar &rarr;
                                </Link>
                            </div>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
