# Technical Guide & Features

## 📖 Table of Contents

- [System Overview](#system-overview)
- [Features](#features)
- [Technical Architecture](#technical-architecture)
- [Database Schema](#database-schema)
- [Authentication System](#authentication-system)
- [Technologies Used](#technologies-used)
- [Application Structure](#application-structure)
- [Security Features](#security-features)
- [API Endpoints](#api-endpoints)
- [Deployment](#deployment)

---

## System Overview

The Inventory Management System is a full-stack web application built with Django that provides comprehensive inventory tracking, user management, and product management capabilities. It features a modern Material Design UI and supports multiple user roles with different permission levels.

### Key Capabilities

- Multi-tenant inventory management
- Role-based access control (RBAC)
- Real-time inventory tracking
- Product metadata management
- User authentication and authorization
- Responsive web interface
- RESTful architecture
- Containerized deployment ready

---

## Features

### 🔐 Authentication & Authorization

**User Registration**
- Email or username-based registration
- Password strength validation
- Email verification support
- Custom user model with extended fields

**Login System**
- Email or username login (EmailOrUsernameBackend)
- Session-based authentication
- Remember me functionality
- Password reset capability
- Secure logout

**User Roles**
- **Admin**: Full system access, user management, system configuration
- **Client**: Manage own inventory, view products, create orders
- **Farmer**: Add products, manage own listings, track inventory

### 📦 Product Management

**Product Operations**
- Create, Read, Update, Delete (CRUD) products
- Product categorization by type (Fresh, Processed, etc.)
- Barcode support for product tracking
- Product metadata (temperature, humidity, storage duration)
- Bulk product operations
- Product search and filtering

**Product Attributes**
- Name, description, category
- Origin/source information
- Lot numbers and batch tracking
- Storage conditions (temperature, humidity, CO2, O2, N2 levels)
- Ethylene management specifications
- Maximum storage duration
- Packaging conditions
- Additional notes

### 👥 User Management

**User Profiles**
- Profile pictures
- Custom user fields
- Client and Farmer specific data
- Account status management
- Plan-based limitations

**Client Management**
- Client registration and approval
- Account status tracking (pending, active, suspended)
- Client-specific inventory views
- Usage limits based on subscription plans

**Farmer Management**
- Farmer profiles with detailed information
- Phone number and location tracking
- Product listings management
- Farmer-to-client relationships

### 📊 Dashboard & Analytics

**Dashboard Features**
- Inventory overview statistics
- Recent activity logs
- Product count summaries
- User statistics
- Quick access to common tasks

**Reporting**
- Product lists with filtering
- Inventory status reports
- User activity reports
- Export capabilities

### 🎨 User Interface

**Material Dashboard UI**
- Clean, modern design
- Responsive layout (mobile, tablet, desktop)
- Sidebar navigation
- RTL (Right-to-Left) support
- Multiple color themes (purple, azure, green, orange, danger, rose)
- Interactive components (modals, alerts, notifications)
- Form validation with visual feedback

**Navigation**
- Sidebar with hierarchical menu
- Breadcrumb navigation
- Quick search functionality
- User profile dropdown
- Mobile-friendly hamburger menu

---

## Technical Architecture

### Architecture Pattern

**MVC (Model-View-Template) Pattern**
```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │ HTTP Request
       ▼
┌─────────────┐
│    URLs     │ ─── Route mapping
└──────┬──────┘
       │
       ▼
┌─────────────┐
│    Views    │ ─── Business Logic
└──────┬──────┘
       │
       ├───► Models ──► Database
       │
       └───► Templates ──► HTML Response
```

### Application Layers

**Presentation Layer**
- HTML Templates (Jinja2)
- CSS (Material Dashboard)
- JavaScript (jQuery, Bootstrap)

**Business Logic Layer**
- Django Views (Function-based and Class-based)
- Forms (Django Forms)
- Custom Validators

**Data Access Layer**
- Django ORM
- Model Managers
- Querysets

**Database Layer**
- SQLite (Development)
- PostgreSQL/MySQL (Production ready)

### Request Flow

```
1. User Request → URL Router
2. URL Router → View Function
3. View → Authenticate User
4. View → Query Models (ORM)
5. Models → Database Query
6. Database → Return Data
7. View → Process Data
8. View → Render Template
9. Template → HTML Response
10. Response → User Browser
```

---

## Database Schema

### Core Models

**CustomUser** (extends Django's AbstractUser)
```python
Fields:
- username (unique)
- email (unique)
- password (hashed)
- is_farmer (boolean)
- is_client (boolean)
- farmer_limit (integer)
- client_limit (integer)
- profile_picture (image)
```

**Client**
```python
Fields:
- user (OneToOne → CustomUser)
- company_name
- phone_number
- address
- account_status (pending/active/suspended)
- registration_date
- plan_type
- product_limit
```

**Farmer**
```python
Fields:
- farmer_id (unique)
- owner (ForeignKey → CustomUser)
- name
- email
- phone
- location
- farm_size
- products (ManyToMany → Product)
```

**Product**
```python
Fields:
- product_name
- product_type (Fresh/Processed/Dried/Frozen)
- origin
- lot_number
- barcode
- ideal_temperature
- relative_humidity
- max_storage_duration
- co2_percentage
- o2_percentage
- n2_percentage
- ethylene_management
- packaging_condition
- additional_notes
- created_by (ForeignKey → CustomUser)
- created_at
- updated_at
```

### Entity Relationships

```
CustomUser (1) ←→ (1) Client
CustomUser (1) ←→ (1) Farmer
Farmer (M) ←→ (M) Product
CustomUser (1) ←→ (M) Product (created_by)
```

---

## Authentication System

### Authentication Backend

**EmailOrUsernameBackend**
- Allows login with email OR username
- Case-insensitive email matching
- Integrated with Django's authentication system

**Configuration**
```python
AUTHENTICATION_BACKENDS = [
    'apps.authentication.backends.EmailOrUsernameBackend',
    'django.contrib.auth.backends.ModelBackend',
]
```

### Session Management

- Session-based authentication (not token-based)
- Configurable session timeout
- Secure session cookies
- CSRF protection enabled

### Password Security

- Django's PBKDF2 password hashing
- Password validators:
  - UserAttributeSimilarityValidator
  - MinimumLengthValidator (8 characters)
  - CommonPasswordValidator
  - NumericPasswordValidator

### Plan-Based Limitations

**Plan System**
- Basic, Standard, Premium tiers
- Limit enforcement via `plan_utils.py`
- Restrictions on:
  - Number of products
  - Number of farmers
  - Number of clients
  - Storage capacity

---

## Technologies Used

### Backend

**Django 5.1.6**
- Web framework
- ORM for database operations
- Built-in admin panel
- Form handling and validation
- Security features

**Python 3.11+**
- Primary programming language
- Required for Django 5.x compatibility

**SQLite3**
- Default development database
- File-based, zero configuration
- Easy to upgrade to PostgreSQL/MySQL

### Frontend

**Material Dashboard**
- Bootstrap 4 based
- Material Design components
- Responsive grid system
- Pre-built UI components

**JavaScript Libraries**
- jQuery 3.x
- Bootstrap 4.x
- Chart.js (for analytics)
- DataTables (for tables)
- Moment.js (date handling)

**CSS/SCSS**
- Material Dashboard SCSS
- Custom styles
- Responsive design
- Theme customization

### Deployment

**Gunicorn**
- WSGI HTTP Server
- Production-ready
- Worker process management
- Configuration: `gunicorn-cfg.py`

**Nginx**
- Reverse proxy
- Static file serving
- Load balancing capability
- SSL/TLS termination

**Docker**
- Containerization
- Multi-container setup (app + nginx)
- Docker Compose orchestration
- Reproducible environments

**WhiteNoise**
- Static file serving for Django
- CDN integration ready
- Compression support

### Development Tools

**python-decouple**
- Environment variable management
- Secure configuration
- `.env` file support

**Pillow**
- Image processing
- Profile picture handling
- Image optimization

---

## Application Structure

### Django Apps

**apps/authentication/**
- User registration and login
- Password reset functionality
- User profile management
- Plan limitation utilities
- Custom authentication backends

**apps/managment/** (Product Management)
- Product CRUD operations
- Farmer management
- Inventory tracking
- Product metadata handling
- Bulk operations

**apps/home/**
- Dashboard views (currently disabled)
- Static pages
- Landing page functionality

### Directory Structure

```
Inventory_System/
│
├── apps/
│   ├── authentication/
│   │   ├── models.py          # CustomUser, Client, Farmer
│   │   ├── views.py           # Login, Register, Profile
│   │   ├── forms.py           # Login/Register forms
│   │   ├── backends.py        # EmailOrUsernameBackend
│   │   ├── plan_utils.py      # Plan limitation logic
│   │   └── signals.py         # User creation signals
│   │
│   ├── managment/
│   │   ├── models.py          # Product model
│   │   ├── views.py           # Product CRUD views
│   │   ├── forms.py           # Product forms
│   │   ├── admin.py           # Admin customization
│   │   └── products.json      # Initial product data
│   │
│   ├── static/
│   │   └── assets/
│   │       ├── css/           # Compiled CSS
│   │       ├── js/            # JavaScript files
│   │       ├── img/           # Images
│   │       └── scss/          # SCSS source files
│   │
│   └── templates/
│       ├── layouts/           # Base templates
│       │   ├── base.html
│       │   └── base-rtl.html
│       ├── includes/          # Reusable components
│       │   ├── sidebar.html
│       │   ├── navigation.html
│       │   ├── footer.html
│       │   └── scripts.html
│       ├── authentication/    # Auth templates
│       └── managment/         # Product templates
│
├── core/
│   ├── settings.py            # Django configuration
│   ├── urls.py                # URL routing
│   ├── wsgi.py                # WSGI config
│   └── asgi.py                # ASGI config (async)
│
├── nginx/
│   └── inventory-app.conf     # Nginx configuration
│
├── docker-compose.yml         # Docker orchestration
├── Dockerfile                 # Docker image definition
├── requirements.txt           # Python dependencies
├── manage.py                  # Django CLI
├── .env                       # Environment variables
└── db.sqlite3                 # Database file
```

---

## Security Features

### Built-in Django Security

**CSRF Protection**
- Token-based CSRF validation
- Automatic form token injection
- Ajax request protection
- Trusted origins configuration

**XSS Prevention**
- Template auto-escaping
- Safe string handling
- Content Security Policy ready

**SQL Injection Prevention**
- Parameterized queries via ORM
- No raw SQL in views
- Query sanitization

**Clickjacking Protection**
- X-Frame-Options header
- Middleware enabled
- Frame denial by default

### Custom Security Measures

**Password Security**
- Strong password requirements
- Hashed storage (PBKDF2)
- No password reuse
- Secure password reset

**Session Security**
- Secure session cookies
- HttpOnly flag
- SameSite cookie policy
- Session timeout

**File Upload Security**
- File type validation
- File size limits
- Secure file storage
- Profile picture validation

**Environment Security**
- Sensitive data in `.env`
- Secret key protection
- Debug mode control
- Allowed hosts configuration

### Production Security Checklist

```python
# core/settings.py (Production)
DEBUG = False
SECRET_KEY = os.environ.get('SECRET_KEY')
ALLOWED_HOSTS = ['yourdomain.com']
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
```

---

## API Endpoints

### Authentication URLs

```
/login/              # POST - User login
/register/           # POST - User registration
/logout/             # GET/POST - User logout
/password-reset/     # POST - Request password reset
/profile/            # GET/POST - User profile
```

### Product Management URLs

```
/products/                    # GET - List all products
/products/add/                # POST - Add new product
/products/<id>/               # GET - View product details
/products/<id>/edit/          # POST - Edit product
/products/<id>/delete/        # POST - Delete product
/products/search/             # GET - Search products
```

### Admin URLs

```
/admin/                       # Django admin panel
/admin/authentication/        # User management
/admin/managment/             # Product management
```

### Static Files

```
/static/                      # Static files (CSS, JS, images)
/media/                       # User uploads (profile pictures)
```

---

## Deployment

### Development Deployment

**Requirements**
- Python 3.11+
- pip
- Virtual environment
- SQLite (included)

**Steps**
```bash
# 1. Create virtual environment
python -m venv .venv

# 2. Activate virtual environment
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run migrations
python manage.py migrate

# 5. Create superuser
python manage.py createsuperuser

# 6. Collect static files
python manage.py collectstatic

# 7. Run development server
python manage.py runserver
```

### Docker Deployment

**Docker Setup**
```yaml
services:
  inventory-app:
    build: .
    container_name: inventory_app
    ports:
      - "5005:5005"
    volumes:
      - ./db.sqlite3:/app/db.sqlite3
      - ./media:/app/core/media
    environment:
      - DEBUG=False
      - SECRET_KEY=${SECRET_KEY}
  
  nginx:
    image: nginx:latest
    container_name: nginx
    ports:
      - "85:85"
    volumes:
      - ./nginx:/etc/nginx/conf.d
    depends_on:
      - inventory-app
```

**Commands**
```bash
# Build and start
docker-compose up -d --build

# View logs
docker logs inventory_app
docker logs nginx

# Stop containers
docker-compose down

# Rebuild
docker-compose up -d --build --force-recreate
```

### Production Deployment

**Environment Configuration**
```env
# .env
DEBUG=False
SECRET_KEY=your-very-secure-secret-key-here
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

**Nginx Configuration**
```nginx
upstream inventory_app {
    server inventory_app:5005;
}

server {
    listen 80;
    server_name yourdomain.com;
    
    location / {
        proxy_pass http://inventory_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /static/ {
        alias /app/staticfiles/;
    }
    
    location /media/ {
        alias /app/core/media/;
    }
}
```

**Gunicorn Configuration**
```python
# gunicorn-cfg.py
bind = '0.0.0.0:5005'
workers = 4  # (2 x CPU cores) + 1
worker_class = 'sync'
timeout = 30
keepalive = 2
accesslog = '-'
errorlog = '-'
loglevel = 'info'
```

### Database Migration to PostgreSQL

**Install PostgreSQL adapter**
```bash
pip install psycopg2-binary
```

**Update settings.py**
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'inventory_db',
        'USER': 'inventory_user',
        'PASSWORD': 'secure_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

**Migrate data**
```bash
# Dump SQLite data
python manage.py dumpdata > data.json

# Switch to PostgreSQL in settings.py

# Create new database schema
python manage.py migrate

# Load data
python manage.py loaddata data.json
```

---

## Performance Optimization

### Database Optimization

- **Indexing**: Add indexes to frequently queried fields
- **Query Optimization**: Use `select_related()` and `prefetch_related()`
- **Connection Pooling**: Implement for high traffic
- **Caching**: Redis/Memcached for session and query caching

### Static Files

- **WhiteNoise**: Efficient static file serving
- **CDN**: CloudFlare or AWS CloudFront
- **Compression**: Gzip/Brotli compression
- **Minification**: Minimize CSS/JS files

### Application Performance

- **Gunicorn Workers**: Adjust based on CPU cores
- **Async Views**: Use for I/O-bound operations
- **Database Connection Pooling**: Reduce overhead
- **Caching Strategy**: Cache frequently accessed data

---

## Monitoring & Logging

### Logging Configuration

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': 'logs/errors.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}
```

### Monitoring Tools

- **Django Debug Toolbar**: Development debugging
- **Sentry**: Error tracking and monitoring
- **New Relic**: Application performance monitoring
- **Prometheus**: Metrics collection
- **Grafana**: Metrics visualization

---

## Testing

### Test Structure

```python
# Example test case
from django.test import TestCase
from apps.authentication.models import CustomUser

class UserModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_user_creation(self):
        self.assertEqual(self.user.username, 'testuser')
        self.assertTrue(self.user.check_password('testpass123'))
```

### Running Tests

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test apps.authentication

# Run with coverage
coverage run manage.py test
coverage report
```

---

## Maintenance

### Regular Tasks

**Database Maintenance**
```bash
# Backup database
python manage.py dumpdata > backup_$(date +%Y%m%d).json

# Clear expired sessions
python manage.py clearsessions

# Database optimization (PostgreSQL)
python manage.py dbshell
VACUUM ANALYZE;
```

**Static Files**
```bash
# Re-collect static files
python manage.py collectstatic --noinput

# Clear old media files
python manage.py cleanup_old_files
```

**Updates**
```bash
# Update dependencies
pip list --outdated
pip install --upgrade <package>

# Update requirements.txt
pip freeze > requirements.txt
```

---

## Contributing

### Development Workflow

1. Create feature branch
2. Make changes
3. Write/update tests
4. Run tests
5. Update documentation
6. Create pull request

### Code Standards

- Follow PEP 8 style guide
- Use meaningful variable names
- Comment complex logic
- Write docstrings for functions
- Keep functions small and focused

---

## Support & Resources

### Documentation

- Django Docs: https://docs.djangoproject.com/
- Material Dashboard Docs: Included in `/static/assets/docs/`
- Python Docs: https://docs.python.org/

### Community

- Django Forum: https://forum.djangoproject.com/
- Stack Overflow: Tag [django]
- GitHub Issues: Project repository

---

**Last Updated**: January 29, 2026
**Version**: 1.0.1
