"use client";

import { Mail, AlertCircle, CheckCircle2 } from "lucide-react";
import { TABS } from "./constants";
import { useCorreos } from "./_hooks/useCorreos";
import { InboxTab } from "./_components/InboxTab";
import { ComposeTab } from "./_components/ComposeTab";
import { InstructTab } from "./_components/InstructTab";
import { DrivePickerModal } from "./_components/DrivePickerModal";

export default function CorreosPage() {
    const c = useCorreos();

    return (
        <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">
            {/* Header */}
            <div className="flex items-start justify-between">
                <div>
                    <h1 className="text-xl font-semibold text-foreground flex items-center gap-2">
                        <Mail className="w-6 h-6 text-violet-400" /> Correos
                    </h1>
                    <p className="text-xs text-muted-foreground mt-1">Envía correos o instruye al agente de email</p>
                </div>
                {c.status && (
                    <div className={`flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border ${
                        c.status.configured
                            ? "bg-green-500/10 text-green-400 border-green-500/30"
                            : "bg-amber-500/10 text-amber-400 border-amber-500/30"
                    }`}>
                        {c.status.configured
                            ? <><CheckCircle2 className="w-3.5 h-3.5" /> Conectado</>
                            : <><AlertCircle className="w-3.5 h-3.5" /> Sin credenciales</>
                        }
                    </div>
                )}
            </div>

            {/* Config warning */}
            {c.status && !c.status.configured && (
                <div className="flex gap-2 text-sm text-amber-400 bg-amber-500/10 border border-amber-500/20 rounded-lg px-4 py-3">
                    <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
                    <span>No hay credenciales de email configuradas. Configura Gmail, Outlook o SMTP en <strong>Configuración &rsaquo; Integraciones</strong>. Los envíos funcionarán en modo demo.</span>
                </div>
            )}

            {/* Tabs */}
            <div className="flex gap-1 border-b border-border">
                {TABS.map(tab => {
                    const Icon = tab.icon;
                    const isActive = c.activeTab === tab.key;
                    return (
                        <button
                            key={tab.key}
                            onClick={() => { c.setActiveTab(tab.key); c.setResult(null); }}
                            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px ${
                                isActive
                                    ? "border-violet-500 text-foreground"
                                    : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
                            }`}
                        >
                            <Icon className="w-4 h-4" />
                            {tab.label}
                        </button>
                    );
                })}
            </div>

            {/* Result banner */}
            {c.result && (
                <div className={`flex gap-2 text-sm rounded-lg px-4 py-3 border ${
                    c.result.ok
                        ? "bg-green-500/10 text-green-400 border-green-500/20"
                        : "bg-red-500/10 text-red-400 border-red-500/20"
                }`}>
                    {c.result.ok ? <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0" /> : <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />}
                    <span>{c.result.message}</span>
                </div>
            )}

            {/* Inbox tab */}
            {c.activeTab === "bandeja" && (
                <InboxTab
                    inboxMessages={c.inboxMessages}
                    inboxLoading={c.inboxLoading}
                    inboxProvider={c.inboxProvider}
                    classMap={c.classMap}
                    loadInbox={c.loadInbox}
                    openMessage={c.openMessage}
                    selectedMsg={c.selectedMsg}
                    bodyLoading={c.bodyLoading}
                    setSelectedMsg={c.setSelectedMsg}
                    setBodyLoading={c.setBodyLoading}
                    draftLoading={c.draftLoading}
                    draftError={c.draftError}
                    handleDraftReply={c.handleDraftReply}
                />
            )}

            {/* Compose tab */}
            {c.activeTab === "componer" && (
                <ComposeTab
                    to={c.to}
                    setTo={c.setTo}
                    subject={c.subject}
                    setSubject={c.setSubject}
                    body={c.body}
                    setBody={c.setBody}
                    attachments={c.attachments}
                    uploading={c.uploading}
                    fileRef={c.fileRef}
                    status={c.status}
                    loading={c.loading}
                    handleSend={c.handleSend}
                    handleAttach={c.handleAttach}
                    removeAttachment={c.removeAttachment}
                    openDrivePicker={c.openDrivePicker}
                />
            )}

            {/* AI instruct tab */}
            {c.activeTab === "ia" && (
                <InstructTab
                    instruction={c.instruction}
                    setInstruction={c.setInstruction}
                    loading={c.loading}
                    handleInstruct={c.handleInstruct}
                />
            )}

            {/* Drive picker modal */}
            {c.showDrive && (
                <DrivePickerModal
                    setShowDrive={c.setShowDrive}
                    driveFiles={c.driveFiles}
                    driveLoading={c.driveLoading}
                    driveQuery={c.driveQuery}
                    setDriveQuery={c.setDriveQuery}
                    importingId={c.importingId}
                    loadDrive={c.loadDrive}
                    attachFromDrive={c.attachFromDrive}
                />
            )}
        </div>
    );
}
