import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { RecruitmentPosition, Candidate } from "@/lib/api/recruitment";

const EMPTY_FORM = { title: "", department: "", description: "", required_skills: "", experience_min_years: 0 };

export function useRecruitment() {
    const [positions, setPositions] = useState<RecruitmentPosition[]>([]);
    const [selectedPos, setSelectedPos] = useState<RecruitmentPosition | null>(null);
    const [candidates, setCandidates] = useState<Candidate[]>([]);
    const [loading, setLoading] = useState(true);
    const [loadingCandidates, setLoadingCandidates] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const [form, setForm] = useState(EMPTY_FORM);

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
        setForm(EMPTY_FORM);
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

    return {
        positions, selectedPos, candidates,
        loading, loadingCandidates, uploading,
        showCreateModal, setShowCreateModal,
        fileInputRef, form, setForm,
        selectPosition, createPosition, handleUploadCV, updateStatus,
    };
}
