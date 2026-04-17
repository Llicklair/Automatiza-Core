"use client";

import { Client } from "@/lib/api";
import { UserPlus, X, DollarSign } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface Props {
    clients: Client[];
    title: string;
    setTitle: (v: string) => void;
    expectedValue: string;
    setExpectedValue: (v: string) => void;
    clientId: string;
    setClientId: (v: string) => void;
    isSubmitting: boolean;
    onSubmit: (e: React.FormEvent) => void;
    onClose: () => void;
}

export function CreateOpportunityModal({
    clients, title, setTitle, expectedValue, setExpectedValue,
    clientId, setClientId, isSubmitting, onSubmit, onClose,
}: Props) {
    return (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <Card className="w-full max-w-lg overflow-hidden shadow-2xl">
                <CardHeader className="p-6 border-b border-border bg-muted/50 flex-row items-center justify-between space-y-0">
                    <CardTitle className="text-lg font-medium text-foreground flex items-center gap-2">
                        <UserPlus className="w-5 h-5 text-primary" /> Nueva Oportunidad
                    </CardTitle>
                    <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onClose}>
                        <X className="w-5 h-5" />
                    </Button>
                </CardHeader>
                <form onSubmit={onSubmit} className="p-6 space-y-5">
                    <div className="space-y-1.5">
                        <Label htmlFor="deal-title">Nombre del Trato</Label>
                        <Input
                            id="deal-title"
                            type="text"
                            required
                            value={title}
                            onChange={e => setTitle(e.target.value)}
                            placeholder="Ej: Renovación Licencias Anuales"
                        />
                    </div>
                    <div className="space-y-1.5">
                        <Label htmlFor="deal-client">Cliente Relacionado</Label>
                        <select
                            id="deal-client"
                            required
                            value={clientId}
                            onChange={e => setClientId(e.target.value)}
                            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                        >
                            <option value="" disabled>Selecciona un cliente</option>
                            {clients.map(c => <option key={c.id} value={c.id}>{c.name} ({c.nif || "Sin NIF"})</option>)}
                        </select>
                    </div>
                    <div className="space-y-1.5">
                        <Label htmlFor="deal-value">Valor Esperado (&euro;)</Label>
                        <div className="relative">
                            <DollarSign className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                            <Input
                                id="deal-value"
                                type="number"
                                required
                                min="0"
                                step="0.01"
                                value={expectedValue}
                                onChange={e => setExpectedValue(e.target.value)}
                                placeholder="0.00"
                                className="pl-10"
                            />
                        </div>
                    </div>
                    <div className="pt-4 flex justify-end gap-3 border-t border-border">
                        <Button type="button" variant="ghost" onClick={onClose}>
                            Cancelar
                        </Button>
                        <Button type="submit" disabled={isSubmitting || !clientId}>
                            {isSubmitting ? "Creando..." : "Crear Trato"}
                        </Button>
                    </div>
                </form>
            </Card>
        </div>
    );
}
