"use client";

import { Video, Plus, Search, Clock, MapPin, ArrowUpRight, VideoOff, Trash2 } from "lucide-react";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import { useTranslations } from "next-intl";
import { EventItem } from "@/lib/api";
import { useReuniones } from "./_hooks/useReuniones";
import { CreateMeetingModal } from "./_components/CreateMeetingModal";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function MeetingsPage() {
    const t = useTranslations("crm");
    const {
        meetings, clients, isLoading,
        search, setSearch,
        showCreate, setShowCreate,
        creating, form, setForm,
        handleCreate, handleDelete,
        upcoming, past,
    } = useReuniones();

    const renderCard = (m: EventItem, isPastMeeting: boolean) => (
        <div key={m.id} className={`p-5 rounded-2xl border transition-all ${isPastMeeting ? "bg-background/40 border-border opacity-70" : "bg-muted border-border hover:border-primary/30"}`}>
            <div className="flex justify-between items-start mb-4">
                <div className="flex items-center gap-3">
                    <div className={`p-2.5 rounded-xl ${isPastMeeting ? "bg-muted" : "bg-primary/10"}`}>
                        <Video className={`w-5 h-5 ${isPastMeeting ? "text-muted-foreground" : "text-primary"}`} />
                    </div>
                    <div>
                        <h3 className={`font-medium ${isPastMeeting ? "text-muted-foreground" : "text-foreground"}`}>{m.title}</h3>
                        <p className="text-xs text-muted-foreground flex items-center gap-1.5 mt-0.5">
                            <Clock className="w-3 h-3" />
                            {format(new Date(m.start_time), "dd MMM, HH:mm", { locale: es })} - {format(new Date(m.end_time), "HH:mm")}
                        </p>
                    </div>
                </div>
                <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 text-muted-foreground hover:text-red-400 hover:bg-red-500/10"
                    onClick={() => handleDelete(m.id)}
                 aria-label={t("reuniones.delete")}>
                    <Trash2 className="w-4 h-4" aria-hidden="true" />
                </Button>
            </div>
            {m.description && <p className="text-sm text-muted-foreground mb-4 line-clamp-2">{m.description}</p>}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <MapPin className="w-3.5 h-3.5" />
                    <span className="truncate max-w-[150px]">{m.location_or_link || t("reuniones.noLocation")}</span>
                </div>
                {!isPastMeeting && m.location_or_link && m.location_or_link.startsWith("http") && (
                    <a href={m.location_or_link} target="_blank" rel="noreferrer"
                        className="flex items-center gap-1 text-xs font-medium text-primary hover:text-primary/80 bg-primary/10 px-3 py-1.5 rounded-lg">
                        {t("reuniones.join")} <ArrowUpRight className="w-3 h-3" />
                    </a>
                )}
            </div>
        </div>
    );

    return (
        <div className="p-8 max-w-[1400px] mx-auto space-y-6">
            <PageHeader
                title={t("reuniones.title")}
                description={t("reuniones.description")}
                icon={Video}
                actions={
                    <Button onClick={() => setShowCreate(true)}>
                        <Plus className="w-4 h-4 mr-2" /> {t("reuniones.schedule")}
                    </Button>
                }
            />

            <div className="bg-card border border-border rounded-2xl p-6 shadow-xl">
                <div className="flex items-center gap-4 mb-8">
                    <div className="relative flex-1 max-w-md">
                        <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                        <Input
                            placeholder={t("reuniones.searchPlaceholder")}
                            value={search}
                            onChange={e => setSearch(e.target.value)}
                            className="pl-10"
                        />
                    </div>
                </div>

                {isLoading ? (
                    <div className="flex justify-center p-12">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
                    </div>
                ) : meetings.length === 0 ? (
                    <div className="text-center py-20 border-2 border-dashed border-border rounded-2xl">
                        <VideoOff className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                        <h3 className="text-lg font-medium text-foreground">{t("reuniones.emptyTitle")}</h3>
                        <p className="text-muted-foreground mt-2">{t("reuniones.emptyDescription")}</p>
                    </div>
                ) : (
                    <div className="space-y-10">
                        {upcoming.length > 0 && (
                            <div>
                                <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-4 flex items-center gap-2">
                                    <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                                    {t("reuniones.upcoming", { count: upcoming.length })}
                                </h2>
                                <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
                                    {upcoming.map(m => renderCard(m, false))}
                                </div>
                            </div>
                        )}
                        {past.length > 0 && (
                            <div>
                                <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-4">
                                    {t("reuniones.past", { count: past.length })}
                                </h2>
                                <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
                                    {past.map(m => renderCard(m, true))}
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </div>

            {showCreate && (
                <CreateMeetingModal
                    clients={clients}
                    form={form}
                    setForm={setForm}
                    creating={creating}
                    onSubmit={handleCreate}
                    onClose={() => setShowCreate(false)}
                />
            )}
        </div>
    );
}
