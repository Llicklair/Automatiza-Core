"use client";
import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import type { Employee, LeaveRequest } from "@/lib/api";

export const LEAVE_TYPE_LABELS: Record<string, string> = {
    baja_medica: "Baja médica",
    vacaciones: "Vacaciones",
    excedencia: "Excedencia",
    otros: "Otros",
};

export const STATUS_LABELS: Record<string, string> = {
    pending: "Pendiente",
    approved: "Aprobada",
    rejected: "Rechazada",
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
            setError("Completa todos los campos obligatorios.");
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
            setError("Error al crear la solicitud.");
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
