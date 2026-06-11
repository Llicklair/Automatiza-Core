"use client";

import { Loader2, Save } from "lucide-react";
import { LogoSection } from "./_components/LogoSection";
import { useConfiguracionEmpresa } from "./_hooks/useConfiguracionEmpresa";
import { PageContainer } from "@/components/shared/PageContainer";

export default function EmpresaConfigPage() {
    const {
        name, setName,
        nif, setNif,
        address, setAddress,
        phone, setPhone,
        contactEmail, setContactEmail,
        loading, saving, error, success,
        handleSave,
    } = useConfiguracionEmpresa();

    return (
        <PageContainer width="3xl">
            <div>
                <h1 className="text-3xl font-bold text-foreground mb-1">Datos de mi empresa</h1>
                <p className="text-muted-foreground text-sm mt-2">
                    Esta información se usa como emisor en las facturas y PDFs generados.
                </p>
                <div className="mt-3 p-4 bg-primary/10 border border-primary/20 rounded-xl text-xs text-primary">
                    <strong>Nota importante:</strong> El <i>Nombre / Razón social</i> que configures aquí será exactamente el que verán tus clientes en los encabezados de presupuestos, albaranes, facturas y correos electrónicos automatizados. Asegúrate de escribirlo tal cual deseas presentarte comercial y legalmente.
                </div>
            </div>

            <div className="bg-card border border-border rounded-2xl p-6">
                {loading ? (
                    <div className="flex items-center justify-center gap-2 text-muted-foreground py-10">
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Cargando datos de empresa…
                    </div>
                ) : (
                    <form onSubmit={handleSave} className="space-y-5">
                        <div className="space-y-1.5">
                            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                                Nombre / Razón social
                            </label>
                            <input
                                type="text"
                                required
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                className="w-full bg-muted border border-border rounded-xl px-4 py-2.5 text-sm text-foreground focus:border-primary/20 outline-none"
                                placeholder="Mi Empresa S.L."
                            />
                        </div>

                        <div className="space-y-1.5">
                            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                                NIF / CIF
                            </label>
                            <input
                                type="text"
                                required
                                value={nif}
                                onChange={(e) => setNif(e.target.value.toUpperCase())}
                                className="w-full bg-muted border border-border rounded-xl px-4 py-2.5 text-sm text-foreground focus:border-primary/20 outline-none uppercase"
                                placeholder="B12345678"
                            />
                        </div>

                        <div className="space-y-1.5">
                            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                                Dirección Fiscal
                            </label>
                            <input
                                type="text"
                                value={address}
                                onChange={(e) => setAddress(e.target.value)}
                                className="w-full bg-muted border border-border rounded-xl px-4 py-2.5 text-sm text-foreground focus:border-primary/20 outline-none"
                                placeholder="Calle Mayor 1, 28001 Madrid"
                            />
                        </div>

                        <div className="space-y-1.5">
                            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                                Teléfono de contacto
                            </label>
                            <input
                                type="tel"
                                value={phone}
                                onChange={(e) => setPhone(e.target.value)}
                                className="w-full bg-muted border border-border rounded-xl px-4 py-2.5 text-sm text-foreground focus:border-primary/20 outline-none"
                                placeholder="+34 600 000 000"
                            />
                        </div>

                        <div className="space-y-1.5">
                            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                                Correo Oficial (Facturación)
                            </label>
                            <input
                                type="email"
                                value={contactEmail}
                                onChange={(e) => setContactEmail(e.target.value)}
                                className="w-full bg-muted border border-border rounded-xl px-4 py-2.5 text-sm text-foreground focus:border-primary/20 outline-none"
                                placeholder="facturacion@miempresa.com"
                            />
                        </div>

                        {error && (
                            <p className="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-xl px-3 py-2">
                                {error}
                            </p>
                        )}
                        {success && (
                            <p className="text-sm text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-xl px-3 py-2">
                                {success}
                            </p>
                        )}

                        <div className="pt-3 border-t border-border flex justify-end">
                            <button
                                type="submit"
                                disabled={saving}
                                className="inline-flex items-center gap-2 bg-primary hover:bg-primary disabled:opacity-50 text-foreground px-5 py-2.5 rounded-xl text-sm font-medium transition shadow-lg shadow-primary/20"
                            >
                                {saving ? (
                                    <>
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                        Guardando…
                                    </>
                                ) : (
                                    <>
                                        <Save className="w-4 h-4" />
                                        Guardar cambios
                                    </>
                                )}
                            </button>
                        </div>
                    </form>
                )}
            </div>

            <LogoSection />
        </PageContainer>
    );
}
