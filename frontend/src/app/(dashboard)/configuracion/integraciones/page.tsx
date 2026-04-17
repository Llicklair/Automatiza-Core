"use client";

import { useConfiguracionIntegraciones } from "./_hooks/useConfiguracionIntegraciones";

export default function IntegracionesPage() {
    const {
        tgStatus,
        tgLoading,
        linkUrl,
        handleTelegramConnect,
        handleTelegramDisconnect,
    } = useConfiguracionIntegraciones();

    return (
        <div className="space-y-8">
            <div>
                <h1 className="text-2xl font-bold text-foreground">Integraciones</h1>
                <p className="text-muted-foreground mt-1">
                    Conecta servicios externos para gestionar tu empresa desde cualquier canal.
                </p>
            </div>

            {/* Telegram */}
            <div className="bg-card rounded-xl border border-border p-6">
                <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 bg-blue-500/20 rounded-lg flex items-center justify-center text-blue-400 text-xl">
                        ✈
                    </div>
                    <div>
                        <h2 className="text-lg font-semibold text-foreground">Telegram</h2>
                        <p className="text-sm text-muted-foreground">
                            Gestiona tu empresa por Telegram: crea facturas, consulta datos, habla con la IA.
                        </p>
                    </div>
                    <div className="ml-auto">
                        {tgStatus?.connected ? (
                            <span className="px-3 py-1 bg-green-500/20 text-green-400 rounded-full text-sm font-medium">
                                Conectado
                            </span>
                        ) : (
                            <span className="px-3 py-1 bg-accent text-muted-foreground rounded-full text-sm">
                                Desconectado
                            </span>
                        )}
                    </div>
                </div>

                {tgStatus?.connected ? (
                    <div className="space-y-3">
                        <div className="flex gap-6 text-sm text-foreground">
                            <span>Chat ID: <code className="text-muted-foreground">{tgStatus.chat_id}</code></span>
                            {tgStatus.username && (
                                <span>Usuario: <code className="text-muted-foreground">@{tgStatus.username}</code></span>
                            )}
                        </div>
                        <button
                            onClick={handleTelegramDisconnect}
                            disabled={tgLoading}
                            className="px-4 py-2 bg-red-600/20 text-red-400 rounded-lg hover:bg-red-600/30 transition text-sm disabled:opacity-50"
                        >
                            {tgLoading ? "Desconectando..." : "Desconectar Telegram"}
                        </button>
                    </div>
                ) : (
                    <div className="space-y-3">
                        {linkUrl ? (
                            <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
                                <p className="text-sm text-blue-300 mb-2">
                                    Abre este enlace en Telegram para completar la vinculación:
                                </p>
                                <a
                                    href={linkUrl}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-blue-400 underline hover:text-blue-300 break-all text-sm"
                                >
                                    {linkUrl}
                                </a>
                                <p className="text-xs text-muted-foreground mt-2">
                                    Esperando vinculación... La página se actualizará automáticamente.
                                </p>
                            </div>
                        ) : (
                            <button
                                onClick={handleTelegramConnect}
                                disabled={tgLoading}
                                className="px-4 py-2 bg-blue-600 text-foreground rounded-lg hover:bg-blue-700 transition text-sm disabled:opacity-50"
                            >
                                {tgLoading ? "Generando enlace..." : "Vincular Telegram"}
                            </button>
                        )}
                        <p className="text-xs text-muted-foreground">
                            Necesitas tener un bot de Telegram configurado en el servidor (TELEGRAM_BOT_TOKEN en .env).
                        </p>
                    </div>
                )}
            </div>

            {/* Placeholder: WhatsApp (próximamente) */}
            <div className="bg-card rounded-xl border border-border p-6 opacity-60">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-green-500/20 rounded-lg flex items-center justify-center text-green-400 text-xl">
                        W
                    </div>
                    <div>
                        <h2 className="text-lg font-semibold text-foreground">WhatsApp Business</h2>
                        <p className="text-sm text-muted-foreground">Próximamente — Atiende a clientes por WhatsApp con IA.</p>
                    </div>
                    <span className="ml-auto px-3 py-1 bg-muted text-muted-foreground rounded-full text-sm">
                        Próximamente
                    </span>
                </div>
            </div>
        </div>
    );
}
