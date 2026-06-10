/**
 * Tesorería (F2.7) — cashflow proyectado + remesas SEPA pain.001.
 */
import { downloadBlob, request } from "./client";

export interface CashflowEvent {
    kind: "invoice_in" | "invoice_out" | "payroll";
    label: string;
    amount: number;
    source_id: string | null;
}

export interface CashflowDay {
    date: string; // YYYY-MM-DD
    opening_balance: number;
    inflow: number;
    outflow: number;
    closing_balance: number;
    events: CashflowEvent[];
}

export interface CashflowAlert {
    date: string;
    deficit: number;
    message: string;
}

export interface CashflowProjection {
    opening_balance: number;
    days_ahead: number;
    series: CashflowDay[];
    summary: {
        total_in: number;
        total_out: number;
        net: number;
        min_balance: number;
        min_balance_date: string;
    };
    alerts: CashflowAlert[];
}

export interface Pain001Order {
    creditor_name: string;
    creditor_iban: string;
    amount_eur: number;
    concept: string;
    end_to_end_id?: string;
}

export interface Pain001Request {
    execution_date: string; // YYYY-MM-DD
    debtor_iban?: string;
    debtor_bic?: string | null;
    orders: Pain001Order[];
}

export interface Pain001Result {
    xml: string;
    summary: {
        msg_id: string;
        nb_of_txs: number;
        control_sum_eur: number;
        debtor_iban: string;
        execution_date: string;
        sha256: string;
    };
}

export interface RemittanceOrder {
    id: string;
    counterparty_name: string;
    counterparty_iban: string;
    amount: number;
    concept: string;
    end_to_end_id: string;
    mandate_id: string | null;
    sequence_type: string | null;
    invoice_id: string | null;
    payroll_id: string | null;
}

export interface Remittance {
    id: string;
    remittance_type: "pain.001" | "pain.008";
    msg_id: string;
    status: "generated" | "sent" | "executed" | "reconciled";
    execution_date: string;
    party_iban: string;
    nb_of_txs: number;
    total_amount: number;
    sha256: string;
    executed_at: string | null;
    bank_transaction_id: string | null;
    created_at: string | null;
    orders?: RemittanceOrder[];
}

export interface RemittanceList {
    items: Remittance[];
    total: number;
}

function triggerXmlDownload(xml: string, filename: string) {
    const blob = new Blob([xml], { type: "application/xml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

export const treasury = {
    cashflow: {
        projection: (daysAhead = 90) =>
            request<CashflowProjection>(
                `/api/v1/treasury/cashflow/projection?days_ahead=${daysAhead}`,
            ),
    },
    sepa: {
        /** Genera el XML pain.001 en memoria y devuelve {xml, summary}. */
        buildPain001: (payload: Pain001Request) =>
            request<Pain001Result>("/api/v1/treasury/sepa/pain001", {
                method: "POST",
                body: JSON.stringify(payload),
            }),
        /** Genera el XML y dispara descarga client-side como archivo .xml. */
        downloadPain001: async (payload: Pain001Request) => {
            const result = await treasury.sepa.buildPain001(payload);
            triggerXmlDownload(result.xml, `${result.summary.msg_id}.xml`);
            return result.summary;
        },
    },
    remittances: {
        list: (params?: { status?: string; limit?: number; offset?: number }) => {
            const q = new URLSearchParams();
            if (params?.status) q.set("status", params.status);
            if (params?.limit) q.set("limit", String(params.limit));
            if (params?.offset) q.set("offset", String(params.offset));
            const qs = q.toString();
            return request<RemittanceList>(
                `/api/v1/treasury/remittances${qs ? `?${qs}` : ""}`,
            );
        },
        get: (id: string) =>
            request<Remittance>(`/api/v1/treasury/remittances/${id}`),
        /** Descarga el XML persistido de la remesa. */
        downloadXml: (id: string, msgId: string) =>
            downloadBlob(`/api/v1/treasury/remittances/${id}/xml`, `${msgId}.xml`),
        updateStatus: (
            id: string,
            status: Remittance["status"],
            bankTransactionId?: string,
        ) =>
            request<Remittance>(`/api/v1/treasury/remittances/${id}/status`, {
                method: "POST",
                body: JSON.stringify({
                    status,
                    bank_transaction_id: bankTransactionId ?? null,
                }),
            }),
    },
};
