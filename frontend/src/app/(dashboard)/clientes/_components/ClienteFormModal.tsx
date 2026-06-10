"use client";

import { useTranslations } from "next-intl";
import { Client } from "@/lib/api";

import { FormModal, FormField } from "@/components/shared";
import { Input } from "@/components/ui/input";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";

import { ClientTypeOption } from "./clientHealth";

interface ClienteFormModalProps {
    isCreating: boolean;
    editingClient: Client | null;
    newClient: Partial<Client>;
    setNewClient: (client: Partial<Client>) => void;
    saving: boolean;
    clientTypeOptions: ClientTypeOption[];
    closeModal: () => void;
    handleCreateClient: (e: React.FormEvent) => void;
}

export function ClienteFormModal({
    isCreating,
    editingClient,
    newClient,
    setNewClient,
    saving,
    clientTypeOptions,
    closeModal,
    handleCreateClient,
}: ClienteFormModalProps) {
    const t = useTranslations("clientes");

    return (
        /* FormModal: Create / Edit */
        <FormModal
            open={isCreating}
            onClose={closeModal}
            title={editingClient ? t("editClient") : t("newClient")}
            description={editingClient ? t("editClientDesc") : t("newClientDesc")}
            onSubmit={handleCreateClient}
            isSubmitting={saving}
            submitLabel={editingClient ? t("saveChanges") : t("createClient")}
            className="sm:max-w-lg"
        >
            <div className="grid grid-cols-2 gap-4">
                <FormField label={t("companyName")} required className="col-span-2">
                    <Input
                        required
                        value={newClient.name || ""}
                        onChange={(e) => setNewClient({ ...newClient, name: e.target.value })}
                        placeholder={t("namePlaceholder")}
                    />
                </FormField>
                <FormField label={t("nif")}>
                    <Input
                        value={newClient.nif || ""}
                        onChange={(e) => setNewClient({ ...newClient, nif: e.target.value })}
                        placeholder={t("nifPlaceholder")}
                        className="uppercase"
                    />
                </FormField>
                <FormField label={t("type")}>
                    <Select
                        value={newClient.client_type || "customer"}
                        onValueChange={(v) => setNewClient({ ...newClient, client_type: v })}
                    >
                        <SelectTrigger>
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            {clientTypeOptions.map((o) => (
                                <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </FormField>
                <FormField label={t("email")}>
                    <Input
                        type="email"
                        value={newClient.email || ""}
                        onChange={(e) => setNewClient({ ...newClient, email: e.target.value })}
                        placeholder={t("emailPlaceholder")}
                    />
                </FormField>
                <FormField label={t("phone")}>
                    <Input
                        type="tel"
                        value={newClient.phone || ""}
                        onChange={(e) => setNewClient({ ...newClient, phone: e.target.value })}
                        placeholder={t("phonePlaceholder")}
                    />
                </FormField>
                <FormField label={t("address")} className="col-span-2">
                    <Input
                        value={newClient.address || ""}
                        onChange={(e) => setNewClient({ ...newClient, address: e.target.value })}
                        placeholder={t("addressPlaceholder")}
                    />
                </FormField>
                <FormField label={t("city")}>
                    <Input
                        value={newClient.city || ""}
                        onChange={(e) => setNewClient({ ...newClient, city: e.target.value })}
                        placeholder={t("cityPlaceholder")}
                    />
                </FormField>
                <FormField label={t("postalCode")}>
                    <Input
                        value={newClient.postal_code || ""}
                        onChange={(e) => setNewClient({ ...newClient, postal_code: e.target.value })}
                        placeholder={t("postalCodePlaceholder")}
                    />
                </FormField>
                <div className="col-span-2 flex items-center gap-2 pt-2">
                    <input
                        id="client-marketing-consent"
                        type="checkbox"
                        checked={!!newClient.marketing_consent}
                        onChange={(e) => setNewClient({ ...newClient, marketing_consent: e.target.checked })}
                        className="h-4 w-4 rounded border-border accent-primary"
                    />
                    <label htmlFor="client-marketing-consent" className="text-sm text-foreground cursor-pointer">
                        {t("marketingConsent")}{" "}
                        <span className="text-xs text-muted-foreground">({t("marketingConsentHint")})</span>
                    </label>
                </div>
            </div>
        </FormModal>
    );
}
