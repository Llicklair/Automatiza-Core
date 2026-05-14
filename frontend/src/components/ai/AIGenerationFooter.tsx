/**
 * AI.BAN — Footer de trazabilidad mostrado bajo cada respuesta del agente.
 *
 * Formato: "Generado por {proveedor} · {modelo} · {tokens} tokens".
 * Refuerza transparencia hacia clientes B2B sofisticados que valoran saber
 * qué LLM ha generado la respuesta concreta.
 */
"use client";

interface Props {
    provider?: string | null;
    model?: string | null;
    tokensIn?: number | null;
    tokensOut?: number | null;
}

export function AIGenerationFooter({ provider, model, tokensIn, tokensOut }: Props) {
    if (!provider && !model && tokensIn == null && tokensOut == null) return null;

    const parts: string[] = [];
    if (provider) parts.push(provider);
    if (model) parts.push(model);
    if (tokensIn != null && tokensOut != null) {
        parts.push(`${tokensIn + tokensOut} tokens`);
    } else if (tokensIn != null) {
        parts.push(`${tokensIn} tokens entrada`);
    } else if (tokensOut != null) {
        parts.push(`${tokensOut} tokens salida`);
    }

    return (
        <p className="mt-1.5 select-text text-[10px] text-muted-foreground">
            <span aria-hidden="true">↳ </span>
            Generado por {parts.join(" · ")}
        </p>
    );
}
