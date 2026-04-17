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
}

export const EMPTY_FORM: EmployeeForm = {
    name: "", nif: "", email: "", department: "", role: "",
    base_salary: "", status: "active",
    join_date: "", contract_end_date: "",
};

export const STATUS_OPTIONS = [
    { label: "Activo", value: "active" },
    { label: "Inactivo", value: "inactive" },
    { label: "De baja", value: "leave" },
];
