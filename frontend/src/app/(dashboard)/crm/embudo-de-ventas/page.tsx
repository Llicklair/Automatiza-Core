"use client";

import { Users, Plus, Search, Building2, DollarSign, Sparkles, Trash2 } from "lucide-react";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import { PageHeader } from "@/components/shared/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { useEmbudoDeVentas } from "./_hooks/useEmbudoDeVentas";
import { CreateOpportunityModal } from "./_components/CreateOpportunityModal";

const STAGES: { id: string; label: string; variant: "info" | "default" | "success" | "destructive" | "warning" }[] = [
    { id: "new", label: "Nuevos", variant: "info" },
    { id: "qualified", label: "Cualificados", variant: "default" },
    { id: "proposal", label: "Propuesta", variant: "warning" },
    { id: "won", label: "Ganados", variant: "success" },
    { id: "lost", label: "Perdidos", variant: "destructive" },
];

export default function CRMPipelinePage() {
    const {
        clients, isLoading,
        showModal, setShowModal,
        search, setSearch,
        taskLoading,
        title, setTitle,
        expectedValue, setExpectedValue,
        clientId, setClientId,
        isSubmitting,
        handleCreate, handleDelete, handleAiQualify,
        formatCurrency, handleDragStart, handleDrop, handleDragOver,
        filteredOpps,
    } = useEmbudoDeVentas();

    return (
        <div className="p-8 max-w-[1400px] mx-auto">
            <PageHeader
                title="Embudo de Ventas (CRM)"
                description="Gestiona tus leads o deja que la IA los cualifique."
                icon={Users}
                actions={
                    <div className="flex items-center gap-2">
                        <div className="relative">
                            <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                            <Input
                                type="text"
                                placeholder="Buscar oportunidad..."
                                value={search}
                                onChange={e => setSearch(e.target.value)}
                                className="pl-10 w-64"
                            />
                        </div>
                        <Button onClick={() => setShowModal(true)} variant="secondary">
                            <Plus className="w-4 h-4 mr-2" /> Nuevo Trato
                        </Button>
                        <Button onClick={handleAiQualify} disabled={taskLoading} variant="outline">
                            <Sparkles className="w-4 h-4 mr-2" /> {taskLoading ? "Enviando..." : "Pedir a la IA"}
                        </Button>
                    </div>
                }
            />

            <div className="flex gap-4 overflow-x-auto pb-8 mt-6 h-[calc(100vh-200px)]">
                {STAGES.map(stage => {
                    const stageOpps = filteredOpps.filter(o => o.stage === stage.id);
                    const totalValue = stageOpps.reduce((sum, o) => sum + o.expected_value, 0);
                    return (
                        <Card
                            key={stage.id}
                            className="flex flex-col min-w-[320px] max-w-[320px] overflow-hidden"
                            onDrop={(e) => handleDrop(e, stage.id)}
                            onDragOver={handleDragOver}
                        >
                            <CardHeader className="p-4 pb-3 bg-muted/50 border-b border-border space-y-1">
                                <div className="flex justify-between items-center">
                                    <CardTitle className="text-sm font-medium text-foreground">{stage.label}</CardTitle>
                                    <Badge variant="secondary" className="text-xs">
                                        {stageOpps.length}
                                    </Badge>
                                </div>
                                <p className="text-sm font-medium text-primary">{formatCurrency(totalValue)}</p>
                            </CardHeader>
                            <CardContent className="flex-1 p-3 space-y-3 overflow-y-auto">
                                {stageOpps.map(opp => (
                                    <Card
                                        key={opp.id}
                                        draggable
                                        onDragStart={(e) => handleDragStart(e, opp.id)}
                                        className="hover:border-primary/30 cursor-grab active:cursor-grabbing transition-colors group relative"
                                    >
                                        <CardContent className="p-4">
                                            <div className="flex justify-between items-start mb-2">
                                                <h4 className="font-medium text-foreground text-sm leading-tight pr-6">{opp.title}</h4>
                                                <Button
                                                    variant="ghost"
                                                    size="icon"
                                                    className="h-6 w-6 absolute right-3 top-3 text-muted-foreground hover:text-destructive"
                                                    onClick={(e) => handleDelete(opp.id, e)}
                                                >
                                                    <Trash2 className="w-3.5 h-3.5" />
                                                </Button>
                                            </div>
                                            <div className="flex items-center gap-2 text-xs text-muted-foreground mb-4">
                                                <Building2 className="w-3 h-3" />
                                                <span className="truncate">{clients.find(c => c.id === opp.client_id)?.name || "Cliente desconocido"}</span>
                                            </div>
                                            <div className="flex items-center justify-between pt-3 border-t border-border">
                                                <div className="flex items-center gap-1.5 text-xs font-medium text-primary">
                                                    <DollarSign className="w-3.5 h-3.5" />
                                                    {formatCurrency(opp.expected_value)}
                                                </div>
                                                <span className="text-[10px] text-muted-foreground">{format(new Date(opp.created_at), "d MMM", { locale: es })}</span>
                                            </div>
                                        </CardContent>
                                    </Card>
                                ))}
                                {stageOpps.length === 0 && (
                                    <div className="h-24 border-2 border-dashed border-border rounded-lg flex items-center justify-center text-muted-foreground text-sm">
                                        Arrastra un trato aquí
                                    </div>
                                )}
                            </CardContent>
                        </Card>
                    );
                })}
            </div>

            {showModal && (
                <CreateOpportunityModal
                    clients={clients}
                    title={title}
                    setTitle={setTitle}
                    expectedValue={expectedValue}
                    setExpectedValue={setExpectedValue}
                    clientId={clientId}
                    setClientId={setClientId}
                    isSubmitting={isSubmitting}
                    onSubmit={handleCreate}
                    onClose={() => setShowModal(false)}
                />
            )}
        </div>
    );
}
