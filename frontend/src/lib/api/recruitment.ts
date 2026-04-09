import { request, getToken, BASE } from "./client";

export interface RecruitmentPosition {
    id: string;
    title: string;
    department: string | null;
    description: string | null;
    required_skills: string[];
    experience_min_years: number;
    salary_range_min: number | null;
    salary_range_max: number | null;
    status: string;
    candidate_count: number;
}

export interface Candidate {
    id: string;
    position_id: string | null;
    name: string;
    email: string | null;
    phone: string | null;
    skills: string[];
    experience_years: number | null;
    languages: { lang: string; level: string }[];
    education: string | null;
    summary: string | null;
    score: number | null;
    score_breakdown: Record<string, number> | null;
    status: string;
    cv_file_path: string | null;
}

export const recruitment = {
    listPositions: (status = "all") =>
        request<RecruitmentPosition[]>(`/api/v1/recruitment/positions?status_filter=${status}`),

    createPosition: (data: {
        title: string;
        department?: string;
        description?: string;
        required_skills?: string[];
        experience_min_years?: number;
        salary_range_min?: number;
        salary_range_max?: number;
    }) => request<RecruitmentPosition>("/api/v1/recruitment/positions", {
        method: "POST",
        body: JSON.stringify(data),
    }),

    listCandidates: (positionId: string) =>
        request<Candidate[]>(`/api/v1/recruitment/positions/${positionId}/candidates`),

    uploadCV: async (positionId: string, file: File): Promise<Candidate> => {
        const token = getToken();
        const form = new FormData();
        form.append("file", file);
        const res = await fetch(`${BASE}/api/v1/recruitment/positions/${positionId}/upload-cv`, {
            method: "POST",
            headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
            body: form,
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            throw new Error(err.detail || res.statusText);
        }
        return res.json();
    },

    updateCandidateStatus: (candidateId: string, status: string) =>
        request<Candidate>(`/api/v1/recruitment/candidates/${candidateId}/status`, {
            method: "PATCH",
            body: JSON.stringify({ status }),
        }),
};
