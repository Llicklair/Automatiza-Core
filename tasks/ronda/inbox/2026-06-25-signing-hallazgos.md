# Inbox /forja — hallazgos en services/signing (2026-06-25, barrido #7) ⚠️ firma digital (peso legal)

0 auto-fixes: todo toca el flujo de firma (legal) o el protocolo AutoFirma → decisión humana.

## ⚠️ El más importante
4. **`autofirma.py:164-177` la firma se marca `has_signature=True` por BÚSQUEDA DE STRINGS, sin
   verificación criptográfica real** [alta]. Insertar la cadena `/Type /Sig` en un binario hace
   que el sistema marque el documento como `signed` (sessions.py:144). Mina el valor legal de la
   firma. Fix: verificar criptográficamente con pyhanko/`cryptography` (o dejar el status en
   `pending_verification` hasta confirmar). Es FEATURE, no patch → planificar.

## Para revisar (flujo callback)
1. **`sessions.py:103` early-return en `status=="signed"` sin tenant** [alta según finder].
   Probablemente by-design: el callback es externo sin tenant y el `session_token` de 128 bits
   es la capability (mismo criterio que aceptamos antes). Revisar si quieres defensa extra.
2. **`sessions.py:103`+`autofirma.py:125` `parsed["session_token"]` nunca se compara con el de
   la URL** [media]. El lookup va por el token de la URL (gobierna la sesión), así que el `id`
   del body ignorado no asocia mal; pero validar que coincide (si viene) es defensa en profundidad.
3. **`sessions.py:103` sesión `failed` reprocesable** [media]. Solo `signed` es idempotente; una
   `failed` puede re-postear y sobreescribir `signed_hash`/`signer_nif`. ¿Rechazar si `status !=
   "pending"`? Cuidado con reintentos legítimos → decisión de máquina de estados.
5. **`autofirma.py:74-83` `doc_hash` no se incluye en el config enviado a AutoFirma** [media]; el
   cliente no puede verificar integridad durante la firma. Además no hay bound de tamaño del doc
   antes del base64 en la URI. Cambio de protocolo → revisar con cuidado.
