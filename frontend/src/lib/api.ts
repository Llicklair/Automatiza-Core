/**
 * Re-export from modular api/ directory for backward compatibility.
 * All consumers importing from "@/lib/api" continue to work unchanged.
 *
 * 2026-05-16: consolidado en `export *` para evitar el "doble barrel" donde
 * tipos nuevos en lib/api/<modulo>.ts quedaban invisibles desde @/lib/api
 * (TS resuelve api.ts antes que api/index.ts). Ver tasks/lessons.md
 * 2026-05-15.
 */
export * from "./api/index";
