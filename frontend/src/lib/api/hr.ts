import { request, downloadBlob } from "./client";

export interface Employee {
    id: string;
    tenant_id: string;
    nif: string | null;
    name: string;
    department: string | null;
    role: string | null;
    base_salary: number | null;
    status: string;
    irpf_rate: number | null;
    join_date: string | null;
    contract_end_date: string | null;
    created_at: string;
    updated_at: string | null;
}

export interface Payroll {
    id: string;
    tenant_id: string;
    employee_id: string;
    period_start: string;
    period_end: string;
    issue_date: string;
    base_salary: number;
    ss_contingencias_comunes: number;
    ss_desempleo: number;
    ss_formacion_profesional: number;
    ss_mei: number;
    irpf: number;
    other_deductions: number;
    deductions: number;
    net_salary: number;
    status: string;
    created_at: string;
    employee?: Employee;
}

export interface PayrollCalculation {
    employee_id: string;
    base_salary: number;
    ss_contingencias_comunes: number;
    ss_desempleo: number;
    ss_formacion_profesional: number;
    ss_mei: number;
    total_ss: number;
    irpf: number;
    deductions: number;
    net_salary: number;
    irpf_rate_applied: number;
}

export const hr = {
    employees: {
        list: () => request<Employee[]>("/api/v1/hr/employees"),
        create: (data: Partial<Employee>) => request<Employee>("/api/v1/hr/employees", { method: "POST", body: JSON.stringify(data) }),
        update: (id: string, data: Partial<Employee>) => request<Employee>(`/api/v1/hr/employees/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
        delete: (id: string) => request(`/api/v1/hr/employees/${id}`, { method: "DELETE" }),
    },
    payrolls: {
        list: () => request<Payroll[]>("/api/v1/hr/payrolls"),
        generate: (data: Partial<Payroll>) => request<Payroll>("/api/v1/hr/payrolls", { method: "POST", body: JSON.stringify(data) }),
        generateAuto: (data: { employee_id: string; period_start: string; period_end: string; issue_date?: string; base_salary?: number; status?: string }) =>
            request<Payroll>("/api/v1/hr/payrolls/auto", { method: "POST", body: JSON.stringify(data) }),
        preview: (employeeId: string) =>
            request<PayrollCalculation>(`/api/v1/hr/employees/${employeeId}/payroll/preview`),
        approve: (id: string) => request<Payroll>(`/api/v1/hr/payrolls/${id}/approve`, { method: "POST" }),
        update: (id: string, data: any) => request<any>(`/api/v1/hr/payrolls/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
        delete: (id: string) => request<void>(`/api/v1/hr/payrolls/${id}`, { method: "DELETE" }),
        downloadPdf: (id: string, filename: string) =>
            downloadBlob(`/api/v1/hr/payrolls/${id}/pdf`, filename),
    }
};
