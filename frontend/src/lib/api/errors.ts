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
