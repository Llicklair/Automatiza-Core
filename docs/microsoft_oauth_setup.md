# Configurar Microsoft OAuth para AutomatizaPyme

## 1. Ir a Azure Portal

1. Ir a https://portal.azure.com/
2. Iniciar sesion con tu cuenta Microsoft (puede ser personal o empresarial)

## 2. Registrar la aplicacion

1. Buscar **"App registrations"** (Registros de aplicaciones) en la barra de busqueda superior
2. Click **New registration** (Nuevo registro)
3. Rellenar:
   - **Name**: `AutomatizaPyme`
   - **Supported account types**: seleccionar **"Accounts in any organizational directory and personal Microsoft accounts"** (Cuentas en cualquier directorio organizativo y cuentas personales de Microsoft)
   - **Redirect URI**: seleccionar **Web** y poner:
     ```
     http://localhost:8080/api/v1/integrations/microsoft/callback
     ```
4. Click **Register**

## 3. Copiar el Application (client) ID

En la pagina de la app recien creada:
1. Copia el **Application (client) ID** — este es tu `MICROSOFT_CLIENT_ID`
2. Lo veras arriba en la seccion "Essentials"

## 4. Crear el Client Secret

1. En el menu lateral, click **Certificates & secrets** (Certificados y secretos)
2. Click **New client secret** (Nuevo secreto de cliente)
3. Descripcion: `AutomatizaPyme`
4. Expiracion: **24 months** (o la que prefieras)
5. Click **Add**
6. **IMPORTANTE**: Copia el **Value** (valor) inmediatamente — solo se muestra una vez
   - Este es tu `MICROSOFT_CLIENT_SECRET`

## 5. Configurar permisos de API

1. En el menu lateral, click **API permissions** (Permisos de API)
2. Click **Add a permission** > **Microsoft Graph** > **Delegated permissions**
3. Buscar y marcar:
   - `Mail.Read`
   - `Mail.Send`
   - `Files.ReadWrite`
   - `User.Read` (normalmente ya esta)
   - `offline_access` (normalmente ya esta)
4. Click **Add permissions**
5. NO es necesario "Grant admin consent" para cuentas personales

## 6. Configurar el .env

Abrir `.env` en la raiz del proyecto y en `backend/.env`, y rellenar:

```env
MICROSOFT_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
MICROSOFT_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
MICROSOFT_REDIRECT_URI=http://localhost:8080/api/v1/integrations/microsoft/callback
```

## 7. Reiniciar el backend

Reiniciar el servidor backend para que tome las nuevas variables de entorno.

## 8. Probar

1. En la UI, ir a Integraciones > Outlook > Conectar con Microsoft
2. Se abre la pantalla de consentimiento de Microsoft
3. Autorizas los permisos
4. Redirige de vuelta a la app y queda conectado

## Notas

- El Client Secret expira segun la duracion que elegiste. Cuando expire, genera uno nuevo y actualiza el .env.
- A diferencia de Google, Microsoft no requiere proceso de verificacion para apps con menos de 100 usuarios.
- Una sola conexion Microsoft habilita tanto Outlook como OneDrive.
