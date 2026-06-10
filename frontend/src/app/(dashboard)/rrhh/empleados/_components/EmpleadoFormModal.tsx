"use client";

import { FormModal, FormField } from "@/components/shared";
import { Input } from "@/components/ui/input";
import {
    Select,
    SelectTrigger,
    SelectValue,
    SelectContent,
    SelectItem,
} from "@/components/ui/select";
import { EmployeeForm, LEAVE_TYPE_OPTIONS } from "../_hooks/useEmpleadosTypes";
export type { EmployeeForm };

// ── Props ────────────────────────────────────────────────────────────────────

export interface EmpleadoFormModalProps {
    open: boolean;
    onClose: () => void;
    editingId: string | null;
    form: EmployeeForm;
    setForm: React.Dispatch<React.SetStateAction<EmployeeForm>>;
    saving: boolean;
    error: string;
    onSubmit: (e: React.FormEvent) => Promise<void>;
}

// ── Component ────────────────────────────────────────────────────────────────

export function EmpleadoFormModal({
    open, onClose, editingId, form, setForm, saving, error, onSubmit,
}: EmpleadoFormModalProps) {
    return (
        <FormModal
            open={open}
            onClose={onClose}
            title={editingId ? "Editar Empleado" : "Nuevo Empleado"}
            onSubmit={onSubmit}
            isSubmitting={saving}
            submitLabel={saving ? "Guardando…" : editingId ? "Guardar cambios" : "Crear empleado"}
        >
            <div className="space-y-4">
                <FormField label="Nombre completo" required>
                    <Input
                        required
                        value={form.name}
                        onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                        placeholder="Ej: María García López"
                    />
                </FormField>

                <div className="grid grid-cols-2 gap-3">
                    <FormField label="NIF">
                        <Input
                            value={form.nif}
                            onChange={(e) => setForm((f) => ({ ...f, nif: e.target.value }))}
                            placeholder="12345678A"
                        />
                    </FormField>
                    <FormField label="Salario base (€/mes)">
                        <Input
                            type="number"
                            value={form.base_salary}
                            onChange={(e) => setForm((f) => ({ ...f, base_salary: e.target.value }))}
                            placeholder="2000"
                        />
                    </FormField>
                </div>

                <div className="grid grid-cols-2 gap-3">
                    <FormField label="Pagas anuales">
                        <Select
                            value={form.num_pagas}
                            onValueChange={(v) => setForm((f) => ({ ...f, num_pagas: v, prorratear_pagas: v === "12" ? false : f.prorratear_pagas }))}
                        >
                            <SelectTrigger>
                                <SelectValue placeholder="12" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="12">12 pagas</SelectItem>
                                <SelectItem value="14">14 pagas (2 extras)</SelectItem>
                            </SelectContent>
                        </Select>
                    </FormField>
                    <FormField label="Jornada">
                        <Select
                            value={form.jornada_tipo}
                            onValueChange={(v) => setForm((f) => ({ ...f, jornada_tipo: v, jornada_horas_semana: v === "completa" ? "" : f.jornada_horas_semana }))}
                        >
                            <SelectTrigger>
                                <SelectValue placeholder="Completa" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="completa">Completa (40h)</SelectItem>
                                <SelectItem value="parcial">Parcial</SelectItem>
                            </SelectContent>
                        </Select>
                    </FormField>
                </div>

                {form.num_pagas === "14" && (
                    <label className="flex items-center gap-2 text-sm text-muted-foreground cursor-pointer">
                        <input
                            type="checkbox"
                            checked={form.prorratear_pagas}
                            onChange={(e) => setForm((f) => ({ ...f, prorratear_pagas: e.target.checked }))}
                            className="h-4 w-4 rounded border-border"
                        />
                        Prorratear pagas extra en la nómina mensual
                    </label>
                )}

                {form.jornada_tipo === "parcial" && (
                    <FormField label="Horas por semana">
                        <Input
                            type="number"
                            min="1"
                            max="40"
                            step="0.5"
                            value={form.jornada_horas_semana}
                            onChange={(e) => setForm((f) => ({ ...f, jornada_horas_semana: e.target.value }))}
                            placeholder="20"
                        />
                    </FormField>
                )}

                <FormField label="Email">
                    <Input
                        type="email"
                        value={form.email}
                        onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                        placeholder="empleado@empresa.com"
                    />
                </FormField>

                <div className="grid grid-cols-2 gap-3">
                    <FormField label="Departamento">
                        <Input
                            value={form.department}
                            onChange={(e) => setForm((f) => ({ ...f, department: e.target.value }))}
                            placeholder="Administración"
                        />
                    </FormField>
                    <FormField label="Cargo">
                        <Input
                            value={form.role}
                            onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}
                            placeholder="Contable"
                        />
                    </FormField>
                </div>

                <FormField label="Estado">
                    <Select
                        value={form.status}
                        onValueChange={(v) => setForm((f) => ({ ...f, status: v, leave_type: v !== "leave" ? "" : f.leave_type }))}
                    >
                        <SelectTrigger>
                            <SelectValue placeholder="Seleccionar estado" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="active">Activo</SelectItem>
                            <SelectItem value="inactive">Inactivo</SelectItem>
                            <SelectItem value="leave">De baja</SelectItem>
                        </SelectContent>
                    </Select>
                </FormField>

                {form.status === "leave" && (
                    <>
                        <FormField label="Tipo de baja">
                            <Select
                                value={form.leave_type}
                                onValueChange={(v) => setForm((f) => ({ ...f, leave_type: v }))}
                            >
                                <SelectTrigger>
                                    <SelectValue placeholder="Seleccionar tipo" />
                                </SelectTrigger>
                                <SelectContent>
                                    {LEAVE_TYPE_OPTIONS.map((o) => (
                                        <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </FormField>
                        <div className="grid grid-cols-2 gap-3">
                            <FormField label="Inicio de baja">
                                <Input
                                    type="date"
                                    value={form.leave_start}
                                    onChange={(e) => setForm((f) => ({ ...f, leave_start: e.target.value }))}
                                />
                            </FormField>
                            <FormField label="Fin de baja (est.)">
                                <Input
                                    type="date"
                                    value={form.leave_end}
                                    onChange={(e) => setForm((f) => ({ ...f, leave_end: e.target.value }))}
                                />
                            </FormField>
                        </div>
                    </>
                )}

                <div className="grid grid-cols-2 gap-3">
                    <FormField label="Fecha de alta">
                        <Input
                            type="date"
                            value={form.join_date}
                            onChange={(e) => setForm((f) => ({ ...f, join_date: e.target.value }))}
                        />
                    </FormField>
                    <FormField label="Fin de contrato">
                        <Input
                            type="date"
                            value={form.contract_end_date}
                            onChange={(e) => setForm((f) => ({ ...f, contract_end_date: e.target.value }))}
                        />
                    </FormField>
                </div>

                {error && (
                    <p className="text-sm text-destructive bg-destructive/10 p-3 rounded-lg">{error}</p>
                )}
            </div>
        </FormModal>
    );
}
