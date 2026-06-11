// Shared types and constants for empleados hooks

export interface EmployeeForm {
    name: string;
    nif: string;
    email: string;
    department: string;
    role: string;
    base_salary: string;
    status: string;
    num_pagas: string;
    prorratear_pagas: boolean;
    jornada_tipo: string;
    jornada_horas_semana: string;
    join_date: string;
    contract_end_date: string;
    leave_type: string;
    leave_start: string;
    leave_end: string;
}

export const EMPTY_FORM: EmployeeForm = {
    name: "", nif: "", email: "", department: "", role: "",
    base_salary: "", status: "active",
    num_pagas: "12", prorratear_pagas: false,
    jornada_tipo: "completa", jornada_horas_semana: "",
    join_date: "", contract_end_date: "",
    leave_type: "", leave_start: "", leave_end: "",
};

// I18N — las constantes guardan `labelKey` (clave bajo el namespace "rrhh");
// el componente traduce en render: t(opt.labelKey).
export const STATUS_OPTIONS = [
    { labelKey: "empleados.status.active", value: "active" },
    { labelKey: "empleados.status.inactive", value: "inactive" },
    { labelKey: "empleados.status.leave", value: "leave" },
];

export const LEAVE_TYPE_OPTIONS = [
    { labelKey: "empleados.leaveTypes.bajaMedica", value: "baja_medica" },
    { labelKey: "empleados.leaveTypes.vacaciones", value: "vacaciones" },
    { labelKey: "empleados.leaveTypes.excedencia", value: "excedencia" },
];
