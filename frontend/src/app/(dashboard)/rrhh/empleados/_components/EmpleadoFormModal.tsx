"use client";

import { useTranslations } from "next-intl";
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
    const t = useTranslations("rrhh");
    return (
        <FormModal
            open={open}
            onClose={onClose}
            title={editingId ? t("empleados.form.editTitle") : t("empleados.form.newTitle")}
            onSubmit={onSubmit}
            isSubmitting={saving}
            submitLabel={saving ? t("empleados.form.saving") : editingId ? t("empleados.form.saveChanges") : t("empleados.form.create")}
        >
            <div className="space-y-4">
                <FormField label={t("empleados.form.fullName")} required>
                    <Input
                        required
                        value={form.name}
                        onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                        placeholder={t("empleados.form.fullNamePlaceholder")}
                    />
                </FormField>

                <div className="grid grid-cols-2 gap-3">
                    <FormField label={t("empleados.form.nif")}>
                        <Input
                            value={form.nif}
                            onChange={(e) => setForm((f) => ({ ...f, nif: e.target.value }))}
                            placeholder="12345678A"
                        />
                    </FormField>
                    <FormField label={t("empleados.form.baseSalary")}>
                        <Input
                            type="number"
                            value={form.base_salary}
                            onChange={(e) => setForm((f) => ({ ...f, base_salary: e.target.value }))}
                            placeholder="2000"
                        />
                    </FormField>
                </div>

                <div className="grid grid-cols-2 gap-3">
                    <FormField label={t("empleados.form.annualPayments")}>
                        <Select
                            value={form.num_pagas}
                            onValueChange={(v) => setForm((f) => ({ ...f, num_pagas: v, prorratear_pagas: v === "12" ? false : f.prorratear_pagas }))}
                        >
                            <SelectTrigger>
                                <SelectValue placeholder="12" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="12">{t("empleados.form.payments12")}</SelectItem>
                                <SelectItem value="14">{t("empleados.form.payments14")}</SelectItem>
                            </SelectContent>
                        </Select>
                    </FormField>
                    <FormField label={t("empleados.form.workday")}>
                        <Select
                            value={form.jornada_tipo}
                            onValueChange={(v) => setForm((f) => ({ ...f, jornada_tipo: v, jornada_horas_semana: v === "completa" ? "" : f.jornada_horas_semana }))}
                        >
                            <SelectTrigger>
                                <SelectValue placeholder={t("empleados.form.workdayFullShort")} />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="completa">{t("empleados.form.workdayFull")}</SelectItem>
                                <SelectItem value="parcial">{t("empleados.form.workdayPartial")}</SelectItem>
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
                        {t("empleados.form.prorate")}
                    </label>
                )}

                {form.jornada_tipo === "parcial" && (
                    <FormField label={t("empleados.form.hoursPerWeek")}>
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

                <FormField label={t("empleados.form.email")}>
                    <Input
                        type="email"
                        value={form.email}
                        onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                        placeholder={t("empleados.form.emailPlaceholder")}
                    />
                </FormField>

                <div className="grid grid-cols-2 gap-3">
                    <FormField label={t("empleados.form.department")}>
                        <Input
                            value={form.department}
                            onChange={(e) => setForm((f) => ({ ...f, department: e.target.value }))}
                            placeholder={t("empleados.form.departmentPlaceholder")}
                        />
                    </FormField>
                    <FormField label={t("empleados.form.role")}>
                        <Input
                            value={form.role}
                            onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}
                            placeholder={t("empleados.form.rolePlaceholder")}
                        />
                    </FormField>
                </div>

                <FormField label={t("empleados.form.status")}>
                    <Select
                        value={form.status}
                        onValueChange={(v) => setForm((f) => ({ ...f, status: v, leave_type: v !== "leave" ? "" : f.leave_type }))}
                    >
                        <SelectTrigger>
                            <SelectValue placeholder={t("empleados.form.selectStatus")} />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="active">{t("empleados.status.active")}</SelectItem>
                            <SelectItem value="inactive">{t("empleados.status.inactive")}</SelectItem>
                            <SelectItem value="leave">{t("empleados.status.leave")}</SelectItem>
                        </SelectContent>
                    </Select>
                </FormField>

                {form.status === "leave" && (
                    <>
                        <FormField label={t("empleados.form.leaveType")}>
                            <Select
                                value={form.leave_type}
                                onValueChange={(v) => setForm((f) => ({ ...f, leave_type: v }))}
                            >
                                <SelectTrigger>
                                    <SelectValue placeholder={t("empleados.form.selectType")} />
                                </SelectTrigger>
                                <SelectContent>
                                    {LEAVE_TYPE_OPTIONS.map((o) => (
                                        <SelectItem key={o.value} value={o.value}>{t(o.labelKey)}</SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </FormField>
                        <div className="grid grid-cols-2 gap-3">
                            <FormField label={t("empleados.form.leaveStart")}>
                                <Input
                                    type="date"
                                    value={form.leave_start}
                                    onChange={(e) => setForm((f) => ({ ...f, leave_start: e.target.value }))}
                                />
                            </FormField>
                            <FormField label={t("empleados.form.leaveEnd")}>
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
                    <FormField label={t("empleados.form.joinDate")}>
                        <Input
                            type="date"
                            value={form.join_date}
                            onChange={(e) => setForm((f) => ({ ...f, join_date: e.target.value }))}
                        />
                    </FormField>
                    <FormField label={t("empleados.form.contractEnd")}>
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
