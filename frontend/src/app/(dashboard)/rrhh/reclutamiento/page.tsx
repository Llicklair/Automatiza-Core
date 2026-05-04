"use client";

import { Briefcase, Plus } from "lucide-react";
import { useRecruitment } from "./_hooks/useRecruitment";
import { PositionList } from "./_components/PositionList";
import { CandidateList } from "./_components/CandidateList";
import { CreatePositionModal } from "./_components/CreatePositionModal";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";

export default function RecruitmentPage() {
    const {
        positions, selectedPos, candidates,
        loading, loadingCandidates, uploading,
        showCreateModal, setShowCreateModal,
        fileInputRef, form, setForm,
        selectPosition, createPosition, handleUploadCV, updateStatus,
    } = useRecruitment();

    return (
        <div className="p-8 max-w-[1400px] mx-auto space-y-6">
            <PageHeader
                title="Reclutamiento"
                description="Gestiona puestos abiertos y analiza CVs con IA."
                icon={Briefcase}
                actions={
                    <Button onClick={() => setShowCreateModal(true)}>
                        <Plus className="w-4 h-4 mr-2" /> Nuevo puesto
                    </Button>
                }
            />

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
