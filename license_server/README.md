# License Server Setup Guide

## Using Supabase (Free)

### Step 1: Create Supabase Account
1. Go to https://supabase.com
2. Sign up for free (no credit card needed)
3. Create a new project

### Step 2: Create Database Tables
1. In Supabase dashboard, go to **SQL Editor**
2. Copy and paste the contents of `supabase_schema.sql`
3. Click **Run** to create the tables

### Step 3: Get Your API Keys
1. Go to **Settings** → **API**
2. Copy:
   - **Project URL** (e.g., `https://xxxxx.supabase.co`)
   - **service_role key** (secret, use for server)

### Step 4: Deploy the Server

#### Option A: Railway (Recommended)
1. Go to https://railway.app
2. Connect your GitHub
3. Create new project → Deploy from GitHub
4. Add environment variables:
   ```
   SUPABASE_URL=https://xxxxx.supabase.co
   SUPABASE_KEY=your-service-role-key
   ADMIN_API_KEY=your-secret-admin-key
   ```
5. Deploy!

#### Option B: Render
1. Go to https://render.com
2. Create new Web Service
3. Connect GitHub repo
4. Set environment variables (same as above)
5. Deploy!

#### Option C: Local Testing
```bash
cd license_server
pip install -r requirements.txt

# Set environment variables
set SUPABASE_URL=https://xxxxx.supabase.co
set SUPABASE_KEY=your-service-role-key
set ADMIN_API_KEY=your-secret-admin-key

# Run server
uvicorn main:app --reload --port 8000
```

### Step 5: Update Client
Edit `license_client.py` and set:
```python
LICENSE_SERVER_URL = "https://your-server-url.railway.app"
```

### Step 6: Access Admin Dashboard
1. Open `admin/index.html` in browser
2. Enter your server URL
3. Enter your ADMIN_API_KEY
4. Login and manage licenses!

## API Endpoints

### Public (Client)
- `POST /api/validate` - Validate license key
- `POST /api/deactivate` - Deactivate machine

### Admin (Requires X-Admin-Key header)
- `GET /admin/licenses` - List all licenses
- `POST /admin/licenses` - Create license
- `PUT /admin/licenses/{key}` - Update license
- `DELETE /admin/licenses/{key}` - Delete license
- `POST /admin/licenses/{key}/toggle` - Enable/disable
- `POST /admin/licenses/{key}/reset` - Reset machines
- `GET /admin/stats` - Dashboard stats
- `GET /admin/logs` - Activity logs
- `POST /admin/bulk/generate` - Bulk create licenses

## Security Notes
- Keep your `ADMIN_API_KEY` secret
- Use `service_role` key for server (not `anon` key)
- The admin dashboard is a static HTML file - host it anywhere
