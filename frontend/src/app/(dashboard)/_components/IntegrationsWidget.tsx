"use client";

import { type GmailMessage, type DriveFile, type OutlookMessage, type OneDriveFile } from "@/lib/api";
import {
    CheckCircle2, XCircle, Mail, HardDrive,
    FileSpreadsheet, FileImage, FileText, File as FileIcon, FolderOpen,
} from "lucide-react";
import Link from "next/link";
import { type DashboardIntegrationsState } from "../_hooks/useDashboard";

type Props = DashboardIntegrationsState;

export function IntegrationsWidget({
    gmailConnected,
    gdriveConnected,
    outlookConnected,
    onedriveConnected,
    gmailMessages,
    driveFiles,
    outlookMessages,
    onedriveFiles,
    activeTab,
    setActiveTab,
}: Props) {
    const anyConnected = gmailConnected || outlookConnected || gdriveConnected || onedriveConnected;

    return (
        <div className="bg-card border border-border rounded-2xl overflow-hidden">
            {/* Header + Tabs */}
            <div className="px-5 py-4 border-b border-border bg-card">
                <div className="flex items-center justify-between">
                    <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
                        <Mail className="w-4 h-4 text-primary" /> Correo y Archivos
                    </h2>
                    <div className="flex items-center gap-2">
                        {gmailConnected && <span className="text-[10px] text-emerald-400 font-medium flex items-center gap-0.5"><CheckCircle2 className="w-2.5 h-2.5" />Gmail</span>}
                        {outlookConnected && <span className="text-[10px] text-emerald-400 font-medium flex items-center gap-0.5"><CheckCircle2 className="w-2.5 h-2.5" />Outlook</span>}
                        {gdriveConnected && <span className="text-[10px] text-emerald-400 font-medium flex items-center gap-0.5"><CheckCircle2 className="w-2.5 h-2.5" />Drive</span>}
                        {onedriveConnected && <span className="text-[10px] text-emerald-400 font-medium flex items-center gap-0.5"><CheckCircle2 className="w-2.5 h-2.5" />OneDrive</span>}
                    </div>
                </div>
                {anyConnected && (
                    <div className="flex gap-1 mt-3">
                        {gmailConnected && (
                            <button onClick={() => setActiveTab("gmail")} className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${activeTab === "gmail" ? "bg-accent text-foreground" : "text-muted-foreground hover:text-foreground"}`}>
                                <Mail className="w-3 h-3" /> Gmail
                            </button>
                        )}
                        {outlookConnected && (
                            <button onClick={() => setActiveTab("outlook")} className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${activeTab === "outlook" ? "bg-accent text-foreground" : "text-muted-foreground hover:text-foreground"}`}>
                                <Mail className="w-3 h-3" /> Outlook
                            </button>
                        )}
                        {gdriveConnected && (
                            <button onClick={() => setActiveTab("drive")} className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${activeTab === "drive" ? "bg-accent text-foreground" : "text-muted-foreground hover:text-foreground"}`}>
                                <HardDrive className="w-3 h-3" /> Drive
                            </button>
                        )}
                        {onedriveConnected && (
                            <button onClick={() => setActiveTab("onedrive")} className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${activeTab === "onedrive" ? "bg-accent text-foreground" : "text-muted-foreground hover:text-foreground"}`}>
                                <HardDrive className="w-3 h-3" /> OneDrive
                            </button>
                        )}
                    </div>
                )}
            </div>

            {/* Content */}
            {!anyConnected ? (
                <div className="p-8 text-center flex flex-col items-center gap-2">
                    <XCircle className="w-8 h-8 text-muted-foreground" />
                    <p className="text-xs text-muted-foreground">No hay servicios conectados</p>
                    <Link href="/integraciones" className="mt-2 text-xs text-primary hover:text-primary transition-colors">
                        Conectar en Integraciones &rarr;
                    </Link>
                </div>
            ) : (activeTab === "gmail" || activeTab === "outlook") ? (
                <div className="divide-y divide-border max-h-[300px] overflow-y-auto">
                    {(() => {
                        const msgs = activeTab === "gmail"
                            ? gmailMessages.map(m => ({ id: m.id, from: m.from.replace(/<.*>/, "").trim(), subject: m.subject, snippet: m.snippet, date: m.date }))
                            : outlookMessages.map(m => ({ id: m.id, from: m.from_name || m.from, subject: m.subject, snippet: m.snippet, date: m.date }));
                        if (msgs.length === 0) return <div className="p-6 text-center text-muted-foreground text-xs">Sin correos recientes</div>;
                        return msgs.map(msg => (
                            <div key={msg.id} className="p-4 hover:bg-accent/50 transition-colors">
                                <div className="flex items-start justify-between gap-2">
                                    <p className="text-xs font-medium text-foreground truncate max-w-[180px]">{msg.from}</p>
                                    <span className="text-[10px] text-muted-foreground whitespace-nowrap">
                                        {msg.date ? new Date(msg.date).toLocaleDateString("es-ES", { day: "2-digit", month: "short" }) : ""}
                                    </span>
                                </div>
                                <p className="text-xs text-muted-foreground font-medium mt-1 truncate">{msg.subject}</p>
                                <p className="text-[11px] text-muted-foreground mt-0.5 line-clamp-1">{msg.snippet}</p>
                            </div>
                        ));
                    })()}
                </div>
            ) : (activeTab === "drive" || activeTab === "onedrive") ? (
                <div className="divide-y divide-border max-h-[300px] overflow-y-auto">
                    {(() => {
                        const files = activeTab === "drive"
                            ? driveFiles.map(f => ({ id: f.id, name: f.name, mime: f.mimeType || "", date: f.modifiedTime }))
                            : onedriveFiles.map(f => ({ id: f.id, name: f.name, mime: f.mimeType || "", date: f.lastModifiedDateTime || "" }));
                        if (files.length === 0) return <div className="p-6 text-center text-muted-foreground text-xs">Sin archivos recientes</div>;
                        return files.map(file => {
                            const icon = file.mime.includes("spreadsheet") ? <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400" />
                                : file.mime.includes("image") ? <FileImage className="w-3.5 h-3.5 text-purple-400" />
                                : file.mime.includes("folder") ? <FolderOpen className="w-3.5 h-3.5 text-yellow-400" />
                                : file.mime.includes("document") ? <FileText className="w-3.5 h-3.5 text-blue-400" />
                                : file.mime.includes("pdf") ? <FileText className="w-3.5 h-3.5 text-red-400" />
                                : <FileIcon className="w-3.5 h-3.5 text-muted-foreground" />;
                            return (
                                <div key={file.id} className="p-4 hover:bg-accent/50 transition-colors flex items-center gap-3">
                                    {icon}
                                    <div className="flex-1 min-w-0">
                                        <p className="text-xs text-foreground truncate">{file.name}</p>
                                        <p className="text-[10px] text-muted-foreground mt-0.5">
                                            {file.date ? new Date(file.date).toLocaleDateString("es-ES", { day: "2-digit", month: "short", year: "numeric" }) : ""}
                                        </p>
                                    </div>
                                </div>
                            );
                        });
                    })()}
                </div>
            ) : null}

            {/* Footer */}
            {anyConnected && (
                <div className="p-3 border-t border-border bg-muted/50 text-center">
                    <Link href="/integraciones" className="text-[11px] font-medium text-muted-foreground hover:text-foreground transition-colors">
                        Gestionar integraciones
                    </Link>
                </div>
            )}
        </div>
    );
}
