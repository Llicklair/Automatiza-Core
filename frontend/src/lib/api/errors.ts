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
