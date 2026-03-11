# Jenga Connect - Deployment Guide

This guide covers deploying the Django backend to **Render** with PostgreSQL, caching, and custom domain support.

## Prerequisites

- GitHub account
- Custom domain (optional)

## Quick Deploy to Render

### Option 1: One-Click Deploy (Recommended)

1. Push your code to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com)
3. Click "New +" and select "Blueprint"
4. Connect your GitHub repository
5. Render will detect `render.yaml` automatically
6. Click "Apply"

### Option 2: Manual Setup

1. **Create PostgreSQL Database**
   - Go to Render Dashboard → New → PostgreSQL
   - Name: `jenga_connect_db`
   - Select Free tier
   - Copy the "Internal Database URL"

2. **Create Web Service**
   - New → Web Service
   - Connect GitHub repository
   - Configure:
     - Build Command: `pip install -r requirements.txt`
     - Start Command: `gunicorn backend.wsgi:application --bind 0.0.0.0:$PORT --workers 2`
   - Add Environment Variables:
     - `DATABASE_URL`: (paste from step 1)
     - `DJANGO_SECRET_KEY`: (generate a secure key)
     - `DJANGO_DEBUG`: `False`
     - `DJANGO_ALLOWED_HOSTS`: `.onrender.com,yourdomain.com`
   - Health Check Path: `/api/health/`

3. **Run Migrations**
   - Go to your web service → Shell
   - Run: `python manage.py migrate`

4. **Create Superuser**
   - Shell: `python manage.py createsuperuser`

5. **Configure Custom Domain** (optional)
   - Service → Settings → Custom Domains
   - Add your domain
   - Update DNS records as shown

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection stringpostgres://user: | `pass@host/db` |
| `DJANGO_SECRET_KEY` | Secret key for sessions/cookies | (generate with `python -c "import secrets; print(secrets.token_urlsafe(50))"`) |
| `DJANGO_DEBUG` | Set to `False` for production | `False` |
| `DJANGO_ALLOWED_HOSTS` | Allowed hostnames | `jenga-connect.onrender.com,yourdomain.com` |
| `REDIS_URL` | Redis cache (optional) | `redis://host:6379/1` |

## Scaling for 1000 Users

### Current Configuration
- **Throttling**: 100 requests/hour per user, 1000 requests/hour for authenticated
- **Workers**: 2 Gunicorn workers
- **Database**: PostgreSQL (handles 1000+ users easily)

### Optimizations Applied
1. **Caching**: Redis cache for frequently accessed data
2. **Database**: PostgreSQL instead of SQLite
3. **Static Files**: WhiteNoise for efficient static file serving
4. **Throttling**: Rate limiting enabled
5. **Health Check**: `/api/health/` for monitoring

### Performance Tips
- Monitor at: Render Dashboard → Your Service → Metrics
- If needed, upgrade to paid tier for Redis
- Consider CDN (Cloudflare free) for media files
- Use database connection pooling

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `/api/health/` | Health check (for Render) |
| `/api/profiles/` | User profiles |
| `/api/hardware_stores/` | Hardware stores |
| `/api/products/` | Products list |
| `/api/orders/` | Orders |
| `/api/orders/place_order/` | Place new order (POST) |
| `/admin/` | Django admin |

## Troubleshooting

### 500 Error on First Request
- Check logs: Service → Logs
- Run migrations: `python manage.py migrate`
- Collect static: `python manage.py collectstatic --noinput`

### Database Connection Error
- Verify DATABASE_URL is set
- Check PostgreSQL is running
- Ensure security group allows connections

### Static Files Not Loading
- Run: `python manage.py collectstatic --noinput`
- Check STATIC_ROOT in settings

## Custom Domain Setup

1. Get your domain's DNS nameservers from Render
2. Add CNAME record:
   - Type: CNAME
   - Name: www or @
   - Value: your-service.onrender.com
3. Wait 5-30 minutes for propagation
4. Enable HTTPS (automatic on Render)

## Security Checklist

- [ ] `DJANGO_SECRET_KEY` is unique and secure
- [ ] `DJANGO_DEBUG` = False
- [ ] `DJANGO_SECURE_SSL_REDIRECT` = True
- [ ] HTTPS enabled (automatic on Render)
- [ ] Custom domain with SSL
- [ ] Admin URL changed from `/admin/`
