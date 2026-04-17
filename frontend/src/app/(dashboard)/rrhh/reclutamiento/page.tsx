"use client";

import { Briefcase, Plus } from "lucide-react";
import { useRecruitment } from "./_hooks/useRecruitment";
import { PositionList } from "./_components/PositionList";
import { CandidateList } from "./_components/CandidateList";
import { CreatePositionModal } from "./_components/CreatePositionModal";

export default function RecruitmentPage() {
    const {
        positions, selectedPos, candidates,
        loading, loadingCandidates, uploading,
        showCreateModal, setShowCreateModal,
        fileInputRef, form, setForm,
        selectPosition, createPosition, handleUploadCV, updateStatus,
    } = useRecruitment();

    return (
        <div className="p-6 max-w-6xl mx-auto space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="p-2.5 rounded-xl bg-violet-500/10 border border-violet-500/20">
                        <Briefcase className="w-5 h-5 text-violet-400" />
                    </div>
                    <div>
                        <h1 className="text-lg font-semibold text-foreground">Reclutamiento</h1>
                        <p className="text-xs text-muted-foreground">Gestiona puestos abiertos y analiza CVs con IA</p>
                    </div>
                </div>
                <button
                    onClick={() => setShowCreateModal(true)}
                    className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-violet-600 hover:bg-violet-500 text-foreground text-xs font-medium transition-colors"
                >
                    <Plus className="w-3.5 h-3.5" /> Nuevo puesto
                </button>
            </div>

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

            {showCreateModal && (
                <CreatePositionModal
                    form={form}
                    setForm={setForm}
                    onClose={() => setShowCreateModal(false)}
                    onCreate={createPosition}
                />
            )}
        </div>
    );
}
