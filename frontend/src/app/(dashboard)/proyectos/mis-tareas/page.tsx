import { redirect } from "next/navigation";

// Fusionada con /proyectos/tareas (audit UX 2026-07-02, P1-3): misma tabla
// ProjectTask con dos presentaciones — ahora es un toggle de vista, no dos rutas.
export default function MisTareasRedirect() {
    redirect("/proyectos/tareas?vista=proyecto");
}
