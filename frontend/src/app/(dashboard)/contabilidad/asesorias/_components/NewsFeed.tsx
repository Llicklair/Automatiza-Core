"use client";

import { Newspaper, Search, ExternalLink } from "lucide-react";

interface NewsFeedProps {
    news: any[];
    filteredNews: any[];
    newsSearch: string;
    setNewsSearch: (v: string) => void;
}

export function NewsFeed({ news, filteredNews, newsSearch, setNewsSearch }: NewsFeedProps) {
    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Newspaper className="w-5 h-5 text-muted-foreground" />
                    <h2 className="text-xl font-semibold text-foreground">Novedades Normativas (BOE)</h2>
                </div>
                <div className="relative hidden sm:block">
                    <Search className="w-4 h-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                    <input
                        type="text"
                        placeholder="Buscar decretos..."
                        value={newsSearch}
                        onChange={e => setNewsSearch(e.target.value)}
                        className="bg-card border border-border rounded-lg py-1.5 pl-9 pr-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary w-64 transition-all"
                    />
                </div>
            </div>

            <div className="grid gap-4">
                {filteredNews.length === 0 ? (
                    <div className="bg-card border border-border rounded-2xl p-8 text-center text-muted-foreground">
                        {news.length === 0
                            ? "No se encontraron novedades recientes del BOE para esta categoría. Consulta la guía normativa de arriba para conocer tus obligaciones vigentes."
                            : `Sin resultados para "${newsSearch}"`}
                    </div>
                ) : (
                    filteredNews.map((item: any, i) => (
                        <a
                            key={i}
                            href={item.url}
                            target="_blank"
                            rel="noreferrer"
                            className="group bg-card border border-border hover:border-primary/20 rounded-2xl p-5 hover:bg-muted transition-all flex flex-col sm:flex-row gap-5 shadow-lg shadow-black/10"
                        >
                            <div className="flex-1">
                                <div className="flex items-center gap-3 mb-2">
                                    <span className="text-xs text-muted-foreground font-medium bg-card px-2 py-1 rounded-md border border-border">
                                        {new Date(item.fecha).toLocaleDateString()}
                                    </span>
                                    {item.relevante_pyme && (
                                        <span className="text-[10px] uppercase font-bold tracking-wider text-amber-400 bg-amber-400/10 px-2 py-1 rounded-md ring-1 ring-amber-400/20">
                                            Relevante para tu negocio
                                        </span>
                                    )}
                                    {item.identificador && (
                                        <span className="text-[10px] font-mono text-muted-foreground">
                                            {item.identificador}
                                        </span>
                                    )}
                                </div>
                                <h3 className="text-foreground font-medium leading-snug group-hover:text-primary transition-colors">
                                    {item.titulo}
                                </h3>
                                <p className="text-muted-foreground text-sm mt-2 line-clamp-2 md:line-clamp-3 leading-relaxed">
                                    {item.descripcion}
                                </p>
                            </div>
                            <div className="flex sm:flex-col justify-end items-center sm:items-center gap-2 shrink-0">
                                <div className="w-10 h-10 rounded-full bg-accent/50 flex items-center justify-center group-hover:bg-primary transition-colors group-hover:shadow-lg group-hover:shadow-primary/20">
                                    <ExternalLink className="w-4 h-4 text-muted-foreground group-hover:text-foreground" />
                                </div>
                            </div>
                        </a>
                    ))
                )}
            </div>
        </div>
    );
}
