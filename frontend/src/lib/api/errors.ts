/**
 * Error tipado para respuestas de la API.
 * Preserva status, detail, requestId y errorType del backend.
 */
export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
    public requestId?: string,
    public errorType?: string,
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

/**
 * Mensaje accionable para mostrar al usuario cuando la IA / el backend no está
 * disponible. Cumple SCOPE.md §5.2 (degradación visible): el ERP sigue siendo
 * usable manualmente aunque el LLM falle.
 */
export const AI_DEGRADATION_MESSAGE =
  "IA no disponible temporalmente. El ERP sigue funcionando: puedes crear facturas y gestionar tus datos manualmente.";

/**
 * Detecta errores de conectividad/disponibilidad que el usuario debe poder
 * interpretar como "la IA o el servidor no responde" (no como un bug de la app):
 *  - fallo de red (status 0 / errorType "network_error")
 *  - upstream caído (502/503/504) — típico cuando el proveedor LLM falla.
 */
export function isConnectivityError(err: unknown): err is ApiError {
  if (!(err instanceof ApiError)) return false;
  return (
    err.errorType === "network_error" ||
    err.status === 0 ||
    err.status === 502 ||
    err.status === 503 ||
    err.status === 504
  );
}

// Throttle compartido: una sola alerta de degradación cada 30 s aunque varios
// catch disparen a la vez (mismo criterio que GlobalErrorListener).
let _lastDegradationToast = 0;

/**
 * Si `err` es un error de conectividad/IA, muestra el aviso accionable
 * `AI_DEGRADATION_MESSAGE` (throttled) y devuelve `true` para que el catch corte
 * su manejo genérico. Si no lo es, devuelve `false` y el catch sigue normal.
 *
 * Uso en páginas que dependen de IA:
 *   catch (err) { if (surfaceIfConnectivity(err)) return; ...manejo normal... }
 *
 * Cubre el hueco de GlobalErrorListener (que solo ve errores NO capturados):
 * los catch explícitos que tragan el error no mostraban la degradación.
 */
export function surfaceIfConnectivity(err: unknown): boolean {
  if (!isConnectivityError(err)) return false;
  const now = Date.now();
  if (now - _lastDegradationToast >= 30_000) {
    _lastDegradationToast = now;
    // Import perezoso para no acoplar la capa lib/api al store de UI en carga.
    import("@/stores/toast")
      .then((m) => m.useToastStore.getState().show(AI_DEGRADATION_MESSAGE, "warning"))
      .catch(() => {});
  }
  return true;
}
