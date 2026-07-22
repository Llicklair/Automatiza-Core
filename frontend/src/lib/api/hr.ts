import { request, requestUpload, downloadBlob } from "./client";

export interface EmployeeDocument {
    id: string;
    file_name: string;
    file_type: string | null;
    file_size: number;
    created_at: string | null;
}

export interface Employee {
    id: string;
    tenant_id: string;
    nif: string | null;
    name: string;
    email: string | null;
    department: string | null;
    role: string | null;
    base_salary: number | null;
    status: string;
    irpf_rate: number | null;
    num_pagas: number | null;
    prorratear_pagas: boolean | null;
    jornada_tipo: string | null;
    jornada_horas_semana: number | null;
    join_date: string | null;
    contract_end_date: string | null;
    leave_type: string | null;
    leave_start: string | null;
    leave_end: string | null;
    created_at: string;
    updated_at: string | null;
}

export interface WorkSchedule {
    id: string;
    employee_id: string;
    day_of_week: number;
    start_time: string;
    end_time: string;
    active: boolean;
}

export interface AttendanceRecord {
    id: string;
    employee_id: string;
    clock_in: string;
    clock_out: string | null;
    date: string;
    notes: string | null;
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
    gross_salary?: number | null;
    devengos_json?: Record<string, number> | null;
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

export interface Expense {
    id: string;
    employee_id: string;
    employee_name: string | null;
    amount: number;
    category: string;
    description: string;
    date: string;
    status: string;
    receipt_filename: string | null;
    notes: string | null;
    created_at: string;
}

export interface LeaveRequest {
    id: string;
    employee_id: string;
    leave_type: string;
    start_date: string;
    end_date: string;
    status: string;
    notes: string | null;
    created_at: string;
}

export interface AttendanceSummaryRow {
    employee_id: string;
    minutos: number;
    horas: number;
    dias: number;
    tramos: number;
    abiertos: number;
}

export const hr = {
    employees: {
        list: () => request<Employee[]>("/api/v1/hr/employees"),
        create: (data: Partial<Employee>) => request<Employee>("/api/v1/hr/employees", { method: "POST", body: JSON.stringify(data) }),
        update: (id: string, data: Partial<Employee>) => request<Employee>(`/api/v1/hr/employees/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
        delete: (id: string) => request(`/api/v1/hr/employees/${id}`, { method: "DELETE" }),
        documents: {
            list: (employeeId: string) =>
                request<EmployeeDocument[]>(`/api/v1/hr/employees/${employeeId}/documents`),
            upload: (employeeId: string, file: File): Promise<EmployeeDocument> => {
                const formData = new FormData();
                formData.append("file", file);
                return requestUpload<EmployeeDocument>(`/api/v1/hr/employees/${employeeId}/documents/upload`, formData);
            },
            download: (employeeId: string, docId: string, fileName: string) =>
                downloadBlob(`/api/v1/hr/employees/${employeeId}/documents/${docId}/download`, fileName),
            delete: (employeeId: string, docId: string) =>
                request<void>(`/api/v1/hr/employees/${employeeId}/documents/${docId}`, { method: "DELETE" }),
        },
    },
    payrolls: {
        list: () => request<Payroll[]>("/api/v1/hr/payrolls"),
        generate: (data: Partial<Payroll>) => request<Payroll>("/api/v1/hr/payrolls", { method: "POST", body: JSON.stringify(data) }),
        generateAuto: (data: { employee_id: string; period_start: string; period_end: string; issue_date?: string; base_salary?: number; horas_extra_importe?: number; status?: string }) =>
            request<Payroll>("/api/v1/hr/payrolls/auto", { method: "POST", body: JSON.stringify(data) }),
        preview: (employeeId: string) =>
            request<PayrollCalculation>(`/api/v1/hr/employees/${employeeId}/payroll/preview`),
        approve: (id: string) => request<Payroll>(`/api/v1/hr/payrolls/${id}/approve`, { method: "POST" }),
        update: (id: string, data: any) => request<any>(`/api/v1/hr/payrolls/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
        delete: (id: string) => request<void>(`/api/v1/hr/payrolls/${id}`, { method: "DELETE" }),
        downloadPdf: (id: string, filename: string) =>
            downloadBlob(`/api/v1/hr/payrolls/${id}/pdf`, filename),
    },
    schedules: {
        list: () => request<Record<string, WorkSchedule[]>>("/api/v1/hr/schedules"),
        getEmployee: (employeeId: string) => request<WorkSchedule[]>(`/api/v1/hr/schedules/${employeeId}`),
        upsert: (employeeId: string, schedules: Omit<WorkSchedule, "id" | "employee_id">[]) =>
            request<WorkSchedule[]>(`/api/v1/hr/schedules/${employeeId}`, {
                method: "POST",
                body: JSON.stringify({ schedules }),
            }),
        aiSuggest: (instruction: string, employeeIds?: string[]) =>
            request<{
                suggestions: { employee_id: string; schedule: Record<string, { start_time: string; end_time: string; active: boolean }> }[];
                rationale: string;
            }>("/api/v1/hr/schedules/ai-suggest", {
                method: "POST",
                body: JSON.stringify({ instruction, employee_ids: employeeIds }),
            }),
        export: (format: "xlsx" | "pdf") =>
            downloadBlob(`/api/v1/hr/schedules/export?format=${format}`, `horarios.${format}`),
    },
    attendance: {
        list: (date?: string) =>
            request<AttendanceRecord[]>(`/api/v1/hr/attendance${date ? `?date=${date}` : ""}`),
        now: () => request<AttendanceRecord[]>("/api/v1/hr/attendance/now"),
        summary: (desde: string, hasta: string) =>
            request<AttendanceSummaryRow[]>(`/api/v1/hr/attendance/summary?desde=${desde}&hasta=${hasta}`),
        clockIn: (employee_id: string, notes?: string) =>
            request<AttendanceRecord>("/api/v1/hr/attendance/clock-in", {
                method: "POST",
                body: JSON.stringify({ employee_id, notes }),
            }),
        clockOut: (attendance_id: string) =>
            request<AttendanceRecord>(`/api/v1/hr/attendance/${attendance_id}/clock-out`, { method: "POST" }),
    },
    expenses: {
        list: (status_filter?: string, employee_id?: string) => {
            const params = new URLSearchParams();
            if (status_filter) params.set("status_filter", status_filter);
            if (employee_id) params.set("employee_id", employee_id);
            const qs = params.toString();
            return request<Expense[]>(`/api/v1/hr/expenses${qs ? `?${qs}` : ""}`);
        },
        create: (data: { employee_id: string; amount: number; category: string; description: string; date: string; notes?: string }) =>
            request<Expense>("/api/v1/hr/expenses", { method: "POST", body: JSON.stringify(data) }),
        approve: (id: string) =>
            request<Expense>(`/api/v1/hr/expenses/${id}/approve`, { method: "POST" }),
        reject: (id: string) =>
            request<Expense>(`/api/v1/hr/expenses/${id}/reject`, { method: "POST" }),
        reimburse: (id: string) =>
            request<Expense>(`/api/v1/hr/expenses/${id}/reimburse`, { method: "POST" }),
        uploadReceipt: (id: string, file: File): Promise<Expense> => {
            const formData = new FormData();
            formData.append("file", file);
            return requestUpload<Expense>(`/api/v1/hr/expenses/${id}/receipt`, formData);
        },
        scanReceipt: (file: File) => {
            const formData = new FormData();
            formData.append("file", file);
            return requestUpload<{
                amount: number;
                vat_amount: number | null;
                vat_rate: number | null;
                date: string;
                merchant: string;
                merchant_nif: string | null;
                category: string;
                description: string;
                confidence: number;
            }>(`/api/v1/hr/expenses/scan`, formData);
        },
        downloadReceipt: (id: string, filename: string) =>
            downloadBlob(`/api/v1/hr/expenses/${id}/receipt`, filename),
        delete: (id: string) =>
            request<void>(`/api/v1/hr/expenses/${id}`, { method: "DELETE" }),
    },
    leaveRequests: {
        list: (status?: string) =>
            request<LeaveRequest[]>(`/api/v1/hr/leave-requests${status ? `?status_filter=${status}` : ""}`),
        create: (data: { employee_id: string; leave_type: string; start_date: string; end_date: string; notes?: string }) =>
            request<LeaveRequest>("/api/v1/hr/leave-requests", { method: "POST", body: JSON.stringify(data) }),
        approve: (id: string) =>
            request<LeaveRequest>(`/api/v1/hr/leave-requests/${id}/approve`, { method: "POST" }),
        reject: (id: string) =>
            request<LeaveRequest>(`/api/v1/hr/leave-requests/${id}/reject`, { method: "POST" }),
        delete: (id: string) =>
            request<void>(`/api/v1/hr/leave-requests/${id}`, { method: "DELETE" }),
    },
};
