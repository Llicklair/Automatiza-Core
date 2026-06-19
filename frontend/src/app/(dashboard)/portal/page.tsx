"use client";
import { User, Briefcase, FileText, Umbrella, Receipt } from "lucide-react";
import { useTranslations } from "next-intl";
import { getToken } from "@/lib/api/client";
import { usePortal } from "./_hooks/usePortal";
import { PortalHeader } from "./_components/PortalHeader";
import { FichaTab } from "./_components/FichaTab";
import { NominasTab } from "./_components/NominasTab";
import { VacacionesTab } from "./_components/VacacionesTab";
import { GastosTab } from "./_components/GastosTab";
import { LeaveRequestModal } from "./_components/LeaveRequestModal";
import { ExpenseModal } from "./_components/ExpenseModal";
import { PageContainer } from "@/components/shared/PageContainer";

export default function PortalPage() {
    const t = useTranslations("portal");
    const {
        isAdmin,
        tab, setTab,
        data, loading,
        employeesList, selectedEmployeeId, readOnly,
        clockBusy, clockError,
        showLeave, setShowLeave, leaveForm, setLeaveForm, saving, leaveError, setLeaveError,
        myExpenses, showExpense, setShowExpense, expenseForm, setExpenseForm, expenseSaving, expenseError, setExpenseError,
        uploadingReceiptId,
        handleSelectEmployee, handleClockIn, handleClockOut,
        handleSubmitExpense, handleUploadReceipt, handleSubmitLeave,
        emp,
    } = usePortal();

    return (
        <PageContainer width="4xl">
            {/* Header */}
            <PortalHeader
                emp={emp}
                data={data}
                isAdmin={isAdmin}
                readOnly={readOnly}
                employeesList={employeesList}
                selectedEmployeeId={selectedEmployeeId}
                clockBusy={clockBusy}
                clockError={clockError}
                onSelectEmployee={handleSelectEmployee}
                onClockIn={handleClockIn}
                onClockOut={handleClockOut}
            />

            {loading && (
                <div className="flex items-center justify-center h-40 text-muted-foreground text-sm">{t("page.loading")}</div>
            )}

            {!loading && !emp && !isAdmin && (
                <div className="rounded-xl border border-border bg-card p-8 text-center space-y-2">
                    <Briefcase className="w-8 h-8 mx-auto text-muted-foreground opacity-40" />
                    <p className="text-sm text-foreground font-medium">{t("page.notLinkedTitle")}</p>
                    <p className="text-xs text-muted-foreground">
                        {t("page.notLinkedHint", { email: (() => { try { const tok = getToken(); if (!tok) return ""; return JSON.parse(atob(tok.split(".")[1])).email; } catch { return ""; } })() })}
                    </p>
                </div>
            )}

            {!loading && !emp && isAdmin && !selectedEmployeeId && (
                <div className="rounded-xl border border-border bg-card p-8 text-center space-y-2">
                    <Briefcase className="w-8 h-8 mx-auto text-muted-foreground opacity-40" />
                    <p className="text-sm text-foreground font-medium">{t("page.selectEmployeeTitle")}</p>
                    <p className="text-xs text-muted-foreground">
                        {t("page.selectEmployeeHint")}
                    </p>
                </div>
            )}

            {!loading && emp && (
                <>
                    {/* Tabs */}
                    <div className="flex gap-1 border-b border-border">
                        {([
                            { id: "ficha", label: t("page.tabFicha"), icon: User },
                            { id: "nominas", label: t("page.tabNominas"), icon: FileText },
                            { id: "vacaciones", label: t("page.tabVacaciones"), icon: Umbrella },
                            { id: "gastos", label: t("page.tabGastos"), icon: Receipt },
                        ] as const).map(({ id, label, icon: Icon }) => (
                            <button
                                key={id}
                                onClick={() => setTab(id)}
                                className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
                                    tab === id
                                        ? "border-primary text-foreground"
                                        : "border-transparent text-muted-foreground hover:text-foreground"
                                }`}
                            >
                                <Icon className="w-4 h-4" /> {label}
                            </button>
                        ))}
                    </div>

                    {/* ── Ficha ── */}
                    {tab === "ficha" && <FichaTab emp={emp} data={data} />}

                    {/* ── Nóminas ── */}
                    {tab === "nominas" && <NominasTab payrolls={data!.payrolls} />}

                    {/* ── Vacaciones ── */}
                    {tab === "vacaciones" && (
                        <VacacionesTab
                            leaveRequests={data!.leave_requests}
                            readOnly={readOnly}
                            onNewRequest={() => { setShowLeave(true); setLeaveError(null); }}
                        />
                    )}

                    {/* ── Gastos ── */}
                    {tab === "gastos" && (
                        <GastosTab
                            myExpenses={myExpenses}
                            readOnly={readOnly}
                            uploadingReceiptId={uploadingReceiptId}
                            onNewExpense={() => { setShowExpense(true); setExpenseError(null); }}
                            onUploadReceipt={handleUploadReceipt}
                        />
                    )}
                </>
            )}

            {/* New leave request modal */}
            <LeaveRequestModal
                open={showLeave}
                onOpenChange={setShowLeave}
                leaveForm={leaveForm}
                setLeaveForm={setLeaveForm}
                saving={saving}
                leaveError={leaveError}
                onSubmit={handleSubmitLeave}
            />
            {/* New expense modal */}
            <ExpenseModal
                open={showExpense}
                onOpenChange={setShowExpense}
                expenseForm={expenseForm}
                setExpenseForm={setExpenseForm}
                expenseSaving={expenseSaving}
                expenseError={expenseError}
                onSubmit={handleSubmitExpense}
            />
        </PageContainer>
    );
}
