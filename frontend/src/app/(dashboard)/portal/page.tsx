"use client";
import { User, Briefcase, FileText, Umbrella, Receipt } from "lucide-react";
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
                <div className="flex items-center justify-center h-40 text-muted-foreground text-sm">Cargando…</div>
            )}

            {!loading && !emp && !isAdmin && (
                <div className="rounded-xl border border-border bg-card p-8 text-center space-y-2">
                    <Briefcase className="w-8 h-8 mx-auto text-muted-foreground opacity-40" />
                    <p className="text-sm text-foreground font-medium">Tu cuenta no está vinculada a ningún empleado</p>
                    <p className="text-xs text-muted-foreground">
                        Pide al administrador que añada tu email ({" "}
                        <span className="font-mono text-xs">{(() => { try { const t = getToken(); if (!t) return ""; return JSON.parse(atob(t.split(".")[1])).email; } catch { return ""; } })()}</span>
                        {" "}) a tu ficha de empleado.
                    </p>
                </div>
            )}

            {!loading && !emp && isAdmin && !selectedEmployeeId && (
                <div className="rounded-xl border border-border bg-card p-8 text-center space-y-2">
                    <Briefcase className="w-8 h-8 mx-auto text-muted-foreground opacity-40" />
                    <p className="text-sm text-foreground font-medium">Selecciona un empleado para previsualizar</p>
                    <p className="text-xs text-muted-foreground">
                        Usa el selector de arriba para ver Mi portal de cualquier persona de tu plantilla.
                    </p>
                </div>
            )}

            {!loading && emp && (
                <>
                    {/* Tabs */}
                    <div className="flex gap-1 border-b border-border">
                        {([
                            { id: "ficha", label: "Mi ficha", icon: User },
                            { id: "nominas", label: "Mis nóminas", icon: FileText },
                            { id: "vacaciones", label: "Mis ausencias", icon: Umbrella },
                            { id: "gastos", label: "Mis gastos", icon: Receipt },
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
