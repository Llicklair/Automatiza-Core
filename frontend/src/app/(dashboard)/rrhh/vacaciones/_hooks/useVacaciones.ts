"use client";
import { useState, useEffect, useCallback } from "react";
import { useTranslations } from "next-intl";
import { api } from "@/lib/api";
import type { Employee, LeaveRequest } from "@/lib/api";

// I18N — config estructural + labelKey; el componente traduce en render.
export const LEAVE_TYPE_LABEL_KEYS: Record<string, string> = {
    baja_medica: "vacaciones.leaveTypes.bajaMedica",
    vacaciones: "vacaciones.leaveTypes.vacaciones",
    excedencia: "vacaciones.leaveTypes.excedencia",
    otros: "vacaciones.leaveTypes.otros",
};

export const STATUS_LABEL_KEYS: Record<string, string> = {
    pending: "vacaciones.status.pending",
    approved: "vacaciones.status.approved",
    rejected: "vacaciones.status.rejected",
};

export type StatusFilter = "all" | "pending" | "approved" | "rejected";

export interface NewRequestForm {
    employee_id: string;
    leave_type: string;
    start_date: string;
    end_date: string;
    notes: string;
}

const EMPTY_FORM: NewRequestForm = {
    employee_id: "",
    leave_type: "vacaciones",
    start_date: "",
    end_date: "",
    notes: "",
};

export function useVacaciones() {
    const t = useTranslations("rrhh");
    const [requests, setRequests] = useState<LeaveRequest[]>([]);
    const [employees, setEmployees] = useState<Employee[]>([]);
    const [loading, setLoading] = useState(true);
    const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
    const [showModal, setShowModal] = useState(false);
    const [form, setForm] = useState<NewRequestForm>(EMPTY_FORM);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const loadData = useCallback(async () => {
        setLoading(true);
        try {
            const [reqs, emps] = await Promise.all([
                api.hr.leaveRequests.list(statusFilter === "all" ? undefined : statusFilter),
                api.hr.employees.list(),
            ]);
            setRequests(reqs);
            setEmployees(emps);
        } catch {
            // keep stale data on error
        } finally {
            setLoading(false);
        }
    }, [statusFilter]);

    useEffect(() => {
        loadData();
    }, [loadData]);

    const getEmployee = (id: string) => employees.find((e) => e.id === id);

    const handleCreate = async () => {
        if (!form.employee_id || !form.leave_type || !form.start_date || !form.end_date) {
            setError(t("vacaciones.requiredFieldsError"));
            return;
        }
        setSaving(true);
        setError(null);
        try {
            await api.hr.leaveRequests.create({
                employee_id: form.employee_id,
                leave_type: form.leave_type,
                start_date: form.start_date,
                end_date: form.end_date,
                notes: form.notes || undefined,
            });
            setShowModal(false);
            setForm(EMPTY_FORM);
            await loadData();
        } catch {
            setError(t("vacaciones.createError"));
        } finally {
            setSaving(false);
        }
    };

    const handleApprove = async (id: string) => {
        try {
            await api.hr.leaveRequests.approve(id);
            await loadData();
        } catch {
            // ignore
        }
    };

    const handleReject = async (id: string) => {
        try {
            await api.hr.leaveRequests.reject(id);
            await loadData();
        } catch {
            // ignore
        }
    };

    const handleDelete = async (id: string) => {
        try {
            await api.hr.leaveRequests.delete(id);
            await loadData();
        } catch {
            // ignore
        }
    };

    const openModal = () => {
        setForm(EMPTY_FORM);
        setError(null);
        setShowModal(true);
    };

    return {
        requests,
        employees,
        loading,
        statusFilter,
        setStatusFilter,
        showModal,
        openModal,
        setShowModal,
        form,
        setForm,
        saving,
        error,
        handleCreate,
        handleApprove,
        handleReject,
        handleDelete,
        getEmployee,
    };
}
