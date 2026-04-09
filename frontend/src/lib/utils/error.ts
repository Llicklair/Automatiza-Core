/**
 * Safely extract an error message from an unknown caught value.
 */
export function getErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  if (typeof error === "string") return error;
  return "Error desconocido";
}
