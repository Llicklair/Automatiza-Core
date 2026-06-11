"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { Briefcase, Plus, FileSearch } from "lucide-react";
import { useRecruitment } from "./_hooks/useRecruitment";
import { PositionList } from "./_components/PositionList";
import { CandidateList } from "./_components/CandidateList";
import { CreatePositionModal } from "./_components/CreatePositionModal";
import { CvAnalysisTab } from "./_components/CvAnalysisTab";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { PageContainer } from "@/components/shared/PageContainer";

type Tab = "vacantes" | "cv";

export default function RecruitmentPage() {
    const {
        positions, selectedPos, candidates,
        loading, loadingCandidates, uploading,
        showCreateModal, setShowCreateModal,
        fileInputRef, form, setForm,
        selectPosition, createPosition, handleUploadCV, updateStatus,
    } = useRecruitment();

    const searchParams = useSearchParams();
    const [tab, setTab] = useState<Tab>(searchParams.get("tab") === "cv" ? "cv" : "vacantes");

    const tabs: { key: Tab; label: string; icon: typeof Briefcase }[] = [
        { key: "vacantes", label: "Vacantes y candidatos", icon: Briefcase },
        { key: "cv", label: "Análisis de CV", icon: FileSearch },
    ];

    return (
        <PageContainer>
            <PageHeader
                title="Reclutamiento"
                description="Gestiona puestos abiertos, analiza CVs con IA y crea candidatos."
                icon={Briefcase}
                actions={
                    tab === "vacantes" ? (
                        <Button onClick={() => setShowCreateModal(true)}>
                            <Plus className="w-4 h-4 mr-2" /> Nuevo puesto
                        </Button>
                    ) : undefined
                }
            />

            {/* Pestañas */}
            <div className="flex items-center gap-1 border-b border-border">
                {tabs.map(t => {
                    const Icon = t.icon;
                    const active = tab === t.key;
                    return (
                        <button
                            key={t.key}
                            onClick={() => setTab(t.key)}
                            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
                                active
                                    ? "border-violet-500 text-foreground"
                                    : "border-transparent text-muted-foreground hover:text-foreground"
                            }`}>
                            <Icon className="w-4 h-4" /> {t.label}
                        </button>
                    );
                })}
            </div>

            {tab === "vacantes" ? (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                    <PositionList
                        positions={positions}
                        selectedPos={selectedPos}
                        loading={loading}
                        onSelect={selectPosition}
                    />
                    <div className="lg:col-span-2 space-y-3">
                        <CandidateList
                            selectedPos={selectedPos}
                            candidates={candidates}
                            loadingCandidates={loadingCandidates}
                            uploading={uploading}
                            fileInputRef={fileInputRef}
                            onUploadCV={handleUploadCV}
                            onUpdateStatus={updateStatus}
                        />
                    </div>
                </div>
            ) : (
                <CvAnalysisTab
                    positions={positions}
                    onCandidateCreated={(positionId) => {
                        const pos = positions.find(p => p.id === positionId);
                        setTab("vacantes");
                        if (pos) selectPosition(pos);
                    }}
                />
            )}

            {showCreateModal && (
                <CreatePositionModal
                    form={form}
                    setForm={setForm}
                    onClose={() => setShowCreateModal(false)}
                    onCreate={createPosition}
                />
            )}
        </PageContainer>
    );
}
