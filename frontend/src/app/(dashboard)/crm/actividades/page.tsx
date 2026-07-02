"use client";

import { useTranslations } from "next-intl";
import { Search, Plus, Bot, UserCircle, Trash2, Activity as ActivityIcon } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { es } from "date-fns/locale";
import { useActividades } from "./_hooks/useActividades";
import { CreateActivityModal } from "./_components/CreateActivityModal";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";

export default function ActivitiesPage() {
    const t = useTranslations("crm");
    const {
        activities, clients, isLoading,
        search, setSearch,
        showModal, setShowModal,
        selectedClient, setSelectedClient,
        type, setType,
        description, setDescription,
        isSubmitting,
        handleCreate, deleteActivity,
        getActivityIcon, getClientName,
    } = useActividades();

    return (
        <div className="p-8 max-w-5xl mx-auto space-y-6">
            <PageHeader
                title={t("actividades.title")}
                description={t("actividades.description")}
                icon={ActivityIcon}
                actions={
                    <Button onClick={() => setShowModal(true)}>
                        <Plus className="w-4 h-4 mr-2" />
                        {t("actividades.newInteraction")}
                    </Button>
                }
            />

            {/* Filters */}
            <div className="bg-card border border-border rounded-2xl p-4 flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
                <div className="relative flex-1">
                    <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                    <Input
                        placeholder={t("actividades.searchPlaceholder")}
                        className="pl-9"
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                    />
                </div>
                <Select
                    value={selectedClient || "all"}
                    onValueChange={(v) => setSelectedClient(v === "all" ? "" : v)}
                >
                    <SelectTrigger className="w-full sm:w-52">
                        <SelectValue placeholder={t("actividades.allClients")} />
                    </SelectTrigger>
                    <SelectContent>
                        <SelectItem value="all">{t("actividades.allClients")}</SelectItem>
                        {clients.map((c) => (
                            <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
                        ))}
                    </SelectContent>
                </Select>
            </div>

            {/* Timeline */}
            <div className="bg-card border border-border rounded-2xl p-6 shadow-lg shadow-black/20">
                {isLoading ? (
                    <div className="flex justify-center p-12">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
                    </div>
                ) : activities.length === 0 ? (
                    <div className="text-center py-20">
                        <ActivityIcon className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                        <h3 className="text-lg font-medium text-foreground">{t("actividades.emptyTitle")}</h3>
                        <p className="text-muted-foreground mt-2 max-w-md mx-auto text-sm">
                            {t("actividades.emptyDescription")}
                        </p>
                        <Button className="mt-4" onClick={() => setShowModal(true)}>
                            <Plus className="w-4 h-4 mr-2" /> {t("actividades.firstInteraction")}
                        </Button>
                    </div>
                ) : (
                    <div className="relative pl-4 space-y-8 before:absolute before:inset-0 before:ml-[31px] before:-translate-x-px before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-border before:to-transparent">
                        {activities.map((act) => {
                            const source = act.metadata_json?.source;
                            return (
                                <div
                                    key={act.id}
                                    className="relative flex items-start gap-4 group"
                                >
                                    {/* Timeline node */}
                                    <div className="flex items-center justify-center w-10 h-10 rounded-full border-2 border-border bg-card shadow shrink-0 z-10 transition-transform group-hover:scale-110">
                                        {getActivityIcon(act.type, source)}
                                    </div>

                                    {/* Card */}
                                    <div className="flex-1 p-4 rounded-xl border border-border bg-muted/30 hover:bg-muted/60 transition-colors shadow-sm">
                                        <div className="flex items-center justify-between mb-2">
                                            <div className="flex items-center gap-2">
                                                <UserCircle className="w-4 h-4 text-muted-foreground" />
                                                <span className="font-medium text-sm text-foreground">
                                                    {getClientName(act.client_id)}
                                                </span>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <time className="text-xs font-mono text-muted-foreground">
                                                    {formatDistanceToNow(new Date(act.created_at), { addSuffix: true, locale: es })}
                                                </time>
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    className="h-6 w-6 text-muted-foreground hover:text-red-400 hover:bg-red-500/10 opacity-0 group-hover:opacity-100 transition-opacity"
                                                    onClick={() => deleteActivity(act.id)}
                                                    title={t("actividades.delete")}
                                                 aria-label={t("actividades.delete")}>
                                                    <Trash2 className="w-3.5 h-3.5" aria-hidden="true" />
                                                </Button>
                                            </div>
                                        </div>
                                        <p className="text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed">
                                            {act.description}
                                        </p>
                                        {source === "ai" && (
                                            <div className="mt-3 pt-3 border-t border-border flex items-center gap-2 text-xs text-primary font-medium">
                                                <Bot className="w-3.5 h-3.5" /> {t("actividades.aiGenerated")}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>

            {showModal && (
                <CreateActivityModal
                    clients={clients}
                    selectedClient={selectedClient}
                    setSelectedClient={setSelectedClient}
                    type={type}
                    setType={setType}
                    description={description}
                    setDescription={setDescription}
                    isSubmitting={isSubmitting}
                    onSubmit={handleCreate}
                    onClose={() => setShowModal(false)}
                />
            )}
        </div>
    );
}
