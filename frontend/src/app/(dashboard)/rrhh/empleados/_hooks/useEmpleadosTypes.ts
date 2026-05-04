// Shared types and constants for empleados hooks

export interface EmployeeForm {
    name: string;
    nif: string;
    email: string;
    department: string;
    role: string;
    base_salary: string;
    status: string;
    join_date: string;
    contract_end_date: string;
    leave_type: string;
    leave_start: string;
    leave_end: string;
}

export const EMPTY_FORM: EmployeeForm = {
    name: "", nif: "", email: "", department: "", role: "",
    base_salary: "", status: "active",
    join_date: "", contract_end_date: "",
    leave_type: "", leave_start: "", leave_end: "",
};

export const STATUS_OPTIONS = [
    { label: "Activo", value: "active" },
    { label: "Inactivo", value: "inactive" },
    { label: "De baja", value: "leave" },
];

export const LEAVE_TYPE_OPTIONS = [
    { label: "Baja médica", value: "baja_medica" },
    { label: "Vacaciones", value: "vacaciones" },
    { label: "Excedencia", value: "excedencia" },
];
