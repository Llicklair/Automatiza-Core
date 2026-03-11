import { Zap, Sparkles } from "lucide-react";

export default function ComingSoon({ title, description }: { title: string, description?: string }) {
    return (
        <div className="flex flex-col flex-1 items-center justify-center min-h-[calc(100vh-64px)] p-6 bg-[#09090b]">
            <div className="max-w-md w-full text-center space-y-6">
                <div className="mx-auto w-16 h-16 bg-indigo-500/10 rounded-2xl flex items-center justify-center border border-indigo-500/20 mb-6 relative">
                    <Zap className="w-8 h-8 text-indigo-400" />
                    <Sparkles className="w-4 h-4 text-purple-400 absolute -top-1 -right-1 animate-pulse" />
                </div>

                <h1 className="text-2xl font-medium text-white">
                    {title}
                </h1>

                <p className="text-zinc-400 text-sm leading-relaxed">
                    {description || "Estamos entrenando a nuestros agentes de Inteligencia Artificial para automatizar esta sección. Muy pronto podrás disfrutar de una gestión híbrida donde la IA hará el trabajo pesado por ti."}
                </p>

                <div className="pt-8">
                    <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#111113] border border-zinc-800 text-xs font-medium text-zinc-300">
                        <span className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse"></span>
                        En Desarrollo
                    </div>
                </div>
            </div>
        </div>
    );
}
