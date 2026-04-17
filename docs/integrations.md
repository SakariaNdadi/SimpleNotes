# Calendar & Task Integrations

## Google Calendar & Tasks

### Setup OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project → APIs & Services → Credentials
3. Create OAuth 2.0 Client ID (Web application)
4. Add authorized redirect URI: `{APP_BASE_URL}/integrations/google/callback`
5. Enable APIs: **Google Calendar API** and **Tasks API**
6. Copy Client ID and Client Secret to `.env`:
   ```
   GOOGLE_CLIENT_ID=your-client-id
   GOOGLE_CLIENT_SECRET=your-client-secret
   ```

## Microsoft Calendar & To Do

### Setup OAuth Credentials

1. Go to [Azure Portal](https://portal.azure.com) → App registrations → New registration
2. Add redirect URI: `{APP_BASE_URL}/integrations/microsoft/callback`
3. Under **Certificates & secrets** → New client secret
4. Under **API permissions** add: `Calendars.ReadWrite`, `Tasks.ReadWrite`, `offline_access`
5. Copy Application (client) ID and secret to `.env`:
   ```
   MICROSOFT_CLIENT_ID=your-client-id
   MICROSOFT_CLIENT_SECRET=your-client-secret
   MICROSOFT_TENANT_ID=common  # or your tenant ID for org accounts
   ```

## How It Works

After connecting, when you save a note the AI analyzes it for tasks and reminders.
If any are found, a prompt appears on the note card letting you create them on your connected platform(s).

Token storage: access tokens and refresh tokens are encrypted at rest using Fernet.
