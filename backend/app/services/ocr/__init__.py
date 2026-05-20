"""OCR services — extracción estructurada de datos desde imágenes (tickets, facturas)."""

from app.services.ocr.receipt_scanner import ReceiptExtractionError, extract_receipt_data

__all__ = ["extract_receipt_data", "ReceiptExtractionError"]
