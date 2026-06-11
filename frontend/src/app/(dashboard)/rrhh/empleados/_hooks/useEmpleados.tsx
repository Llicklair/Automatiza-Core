"use client";

import { useEmpleadosCRUD } from "./useEmpleadosCRUD";
import { useEmpleadosUpload } from "./useEmpleadosUpload";
import { STATUS_OPTIONS } from "./useEmpleadosTypes";
import type { Employee, Payroll } from "@/lib/api";
import type { ColumnDef } from "@tanstack/react-table";
import type { EmployeeForm } from "./useEmpleadosTypes";

// Re-export so existing imports from this file continue to work
export { STATUS_OPTIONS };
export type { EmployeeForm };

export interface UseEmpleadosReturn {
    // Data
    employees: Employee[];
    isLoading: boolean;
    columns: ColumnDef<Employee>[];
    departmentOptions: { label: string; value: string }[];
    activeCount: number;
    totalSalary: number;

    // Form modal
    form: EmployeeForm;
    setForm: React.Dispatch<React.SetStateAction<EmployeeForm>>;
    showModal: boolean;
    setShowModal: (v: boolean) => void;
    editingId: string | null;
    saving: boolean;
    error: string;
    openModal: () => void;
    handleSubmit: (e: React.FormEvent) => Promise<void>;

    // Payroll drawer
    selectedEmp: Employee | null;
    setSelectedEmp: (emp: Employee | null) => void;
    empPayrolls: Payroll[];
    loadingPayrolls: boolean;
    openPayrolls: (emp: Employee) => Promise<void>;

    // Docs modal
    docsEmp: Employee | null;
    setDocsEmp: (emp: Employee | null) => void;
}

/** Composer: combines CRUD + upload concerns. Public API is unchanged. */
export function useEmpleados(): UseEmpleadosReturn {
    const upload = useEmpleadosUpload();
    const crud = useEmpleadosCRUD(upload.setDocsEmp);

    return {
        ...crud,
        docsEmp: upload.docsEmp,
        setDocsEmp: upload.setDocsEmp,
    };
}
