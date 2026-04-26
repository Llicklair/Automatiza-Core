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
import { EmployeeForm } from "../_hooks/useEmpleados";

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
                        onValueChange={(v) => setForm((f) => ({ ...f, status: v }))}
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
