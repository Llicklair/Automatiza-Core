"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useFormat } from "@/hooks/useFormat";
import { Users, Plus, Wallet, ShieldCheck, Upload } from "lucide-react";
import { useEmpleados, STATUS_OPTIONS } from "./_hooks/useEmpleados";
import { EmployeeDocsModal } from "./_components/EmployeeDocsModal";
import { EmpleadoFormModal } from "./_components/EmpleadoFormModal";
import { PayrollDrawer } from "./_components/PayrollDrawer";

import { PageHeader } from "@/components/shared/PageHeader";
import { KpiCard } from "@/components/shared/KpiCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { DataTable } from "@/components/data-table";
import { Button } from "@/components/ui/button";
import { exportToCsv } from "@/lib/utils/export-csv";
import type { Employee } from "@/lib/api";
import { api } from "@/lib/api";
import { ImportCsvModal } from "@/components/shared/ImportCsvModal";
import { PageContainer } from "@/components/shared/PageContainer";

export default function EmployeesPage() {
    const {
        employees, isLoading, columns, departmentOptions, activeCount, totalSalary,
        form, setForm, showModal, setShowModal, editingId, saving, error, openModal, handleSubmit,
        selectedEmp, setSelectedEmp, empPayrolls, loadingPayrolls,
        docsEmp, setDocsEmp,
    } = useEmpleados();

    const [showImport, setShowImport] = useState(false);
    const t = useTranslations("rrhh");
    const { fmtCurrency } = useFormat();

    const handleExport = () =>
        exportToCsv<Employee>("empleados", employees, [
            { header: t("empleados.csv.name"), accessor: (e) => e.name },
            { header: t("empleados.csv.nif"), accessor: (e) => e.nif ?? "" },
            { header: t("empleados.csv.email"), accessor: (e) => e.email ?? "" },
            { header: t("empleados.csv.department"), accessor: (e) => e.department ?? "" },
            { header: t("empleados.csv.role"), accessor: (e) => e.role ?? "" },
            { header: t("empleados.csv.baseSalary"), accessor: (e) => e.base_salary ?? "" },
            { header: t("empleados.csv.status"), accessor: (e) => e.status },
            { header: t("empleados.csv.joinDate"), accessor: (e) => e.join_date ?? "" },
        ]);

    return (
        <PageContainer width="full">
            {docsEmp && <EmployeeDocsModal employee={docsEmp} onClose={() => setDocsEmp(null)} />}

            <PageHeader
                title={t("empleados.title")}
                description={t("empleados.description")}
                icon={Users}
                actions={
                    <div className="flex gap-2">
                        <Button variant="outline" size="sm" onClick={() => setShowImport(true)}>
                            <Upload className="mr-2 h-4 w-4" /> {t("empleados.importCsv")}
                        </Button>
                        <Button onClick={openModal}>
                            <Plus className="mr-2 h-4 w-4" /> {t("empleados.addEmployee")}
                        </Button>
                    </div>
                }
            />

            {/* KPIs */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <KpiCard title={t("empleados.kpi.activeHeadcount")} value={activeCount} icon={Users} />
                <KpiCard title={t("empleados.kpi.monthlySalaryCost")} value={fmtCurrency(totalSalary)} icon={Wallet} />
                <KpiCard
                    title={t("empleados.kpi.legalStatus")}
                    value={t("empleados.kpi.legalStatusOk")}
                    icon={ShieldCheck}
                    description={t("empleados.kpi.legalStatusDescription")}
                />
            </div>

            {/* Table */}
            {employees.length === 0 && !isLoading ? (
                <EmptyState
                    icon={Users}
                    title={t("empleados.emptyTitle")}
                    description={t("empleados.emptyDescription")}
                    action={{ label: t("empleados.addFirst"), onClick: openModal }}
                />
            ) : (
                <DataTable
                    columns={columns}
                    data={employees}
                    searchKey="name"
                    searchPlaceholder={t("empleados.searchPlaceholder")}
                    isLoading={isLoading}
                    emptyMessage={t("empleados.noResults")}
                    facetedFilters={[
                        { column: "status", title: t("empleados.table.status"), options: STATUS_OPTIONS.map(o => ({ label: t(o.labelKey), value: o.value })) },
                        { column: "department", title: t("empleados.table.department"), options: departmentOptions },
                    ]}
                    onExport={handleExport}
                />
            )}

            {/* Employee form modal */}
            <EmpleadoFormModal
                open={showModal}
                onClose={() => setShowModal(false)}
                editingId={editingId}
                form={form}
                setForm={setForm}
                saving={saving}
                error={error}
                onSubmit={handleSubmit}
            />

            {/* Import CSV modal */}
            <ImportCsvModal
                open={showImport}
                onClose={() => setShowImport(false)}
                entityName="empleados"
                columns={[
                    { header: t("empleados.csv.name"), field: "nombre", required: true, example: "Ana García" },
                    { header: t("empleados.csv.nif"), field: "nif", example: "12345678A" },
                    { header: t("empleados.csv.email"), field: "email", example: "ana@empresa.com" },
                    { header: t("empleados.csv.department"), field: "departamento", example: "Ventas" },
                    { header: t("empleados.csv.role"), field: "rol", example: "Comercial" },
                    { header: t("empleados.csv.baseSalary"), field: "salario_base", example: "28000" },
                    { header: t("empleados.csv.irpf"), field: "irpf", example: "15" },
                    { header: t("empleados.csv.status"), field: "estado", example: "active" },
                ]}
                onImport={(rows) => api.importBulk.employees(rows)}
                onSuccess={() => window.location.reload()}
            />

            {/* Payroll drawer */}
            {selectedEmp && (
                <PayrollDrawer
                    selectedEmp={selectedEmp}
                    onClose={() => setSelectedEmp(null)}
                    empPayrolls={empPayrolls}
                    loadingPayrolls={loadingPayrolls}
                />
            )}
        </PageContainer>
    );
}
