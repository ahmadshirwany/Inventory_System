# Inventory Management System

![version](https://img.shields.io/badge/version-1.0.1-blue.svg)

A modern web-based inventory management system built with Django and Material Dashboard UI.

## ✨ Features

- 🔐 **User Authentication** - Secure login and registration system
- 📦 **Product Management** - Add, edit, and track inventory items
- 👥 **Multi-user Support** - Different roles (Admin, Client, Farmer)
- 🎨 **Modern UI** - Clean Material Design interface
- 📊 **Dashboard** - Overview of inventory statistics
- 🗄️ **Database** - SQLite database (easy to upgrade to PostgreSQL/MySQL)
- 🐳 **Docker Ready** - Easy deployment with Docker
- 📱 **Responsive** - Works on desktop, tablet, and mobile

## 📋 Requirements

- Python 3.10 or higher
- pip (Python package manager)
- Docker (optional, for containerized deployment)

## ⚠️ Security Setup (Important!)

Before running the application, you must configure environment variables:

1. Copy the example files:
   ```bash
   cp .env.example .env
   cp IP_data.json.example IP_data.json
   ```

2. Edit `.env` and set your `SECRET_KEY` and other settings

3. Edit `IP_data.json` with your server details

📖 **Read [SECURITY.md](SECURITY.md) for detailed security instructions before deploying!**

## 🚀 Quick Start

### Option 1: Run Locally (Without Docker)

**1. Clone the repository**

**1. Clone the repository**
```bash
git clone <your-repository-url>
cd Inventory_System
```

**2. Create a virtual environment**
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/Mac
python3 -m venv .venv
source .venv/bin/activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Set up the database**
```bash
python manage.py migrate
```

**5. Create a superuser (admin account)**
```bash
python manage.py createsuperuser
```

**6. Run the development server**
```bash
python manage.py runserver
```

**7. Open your browser**
```
http://127.0.0.1:8000/
```

### Option 2: Run with Docker

**1. Make sure Docker is installed and running**

**2. Build and start the containers**
```bash
docker-compose up -d --build
```

**3. Access the application**
```
http://localhost:85
```

**4. Stop the containers**
```bash
docker-compose down
```

## 📂 Project Structure

```
Inventory_System/
├── apps/
│   ├── authentication/      # User login & registration
│   ├── managment/          # Product & inventory management
│   ├── static/             # CSS, JavaScript, images
│   └── templates/          # HTML templates
├── core/
│   ├── settings.py         # Django configuration
│   ├── urls.py            # URL routing
│   └── wsgi.py            # WSGI configuration
├── docker-compose.yml      # Docker setup
├── Dockerfile             # Docker image definition
├── requirements.txt       # Python dependencies
└── manage.py             # Django management script
```

## 🔧 Configuration

**Environment Variables**

Edit the `.env` file to configure:
```env
DEBUG=True
SECRET_KEY=your-secret-key-here
SERVER=localhost
```

**IP Configuration**

The `IP_data.json` file contains IP settings:
```json
{
  "IP": "your-server-ip"
}
```

## 👤 User Roles

- **Admin** - Full access to manage everything
- **Client** - Can view and manage their inventory
- **Farmer** - Can add and track their products

## 🎨 Customization

### Change Theme Colors

Edit the sidebar color in templates:
```html
<div class="sidebar" data-color="purple">
```

Available colors: `purple`, `azure`, `green`, `orange`, `danger`, `rose`

## 📝 Common Tasks

**Create a new user**
```bash
python manage.py createsuperuser
```

**Reset database**
```bash
python manage.py flush
```

**Collect static files**
```bash
python manage.py collectstatic
```

**Run migrations**
```bash
python manage.py makemigrations
python manage.py migrate
```

## 🐛 Troubleshooting

**Port already in use**
```bash
# Use a different port
python manage.py runserver 8080
```

**CSRF errors**
- Make sure `ALLOWED_HOSTS` in `settings.py` includes your domain
- Check that `CSRF_TRUSTED_ORIGINS` is properly configured

**Docker issues**
```bash
# Rebuild containers
docker-compose down
docker-compose up -d --build

# View logs
docker logs inventory_app
```

## 📄 License

MIT License - Copyright 2026 Inventory Management System

## 🤝 Support

For questions or issues:
- Check the troubleshooting section
- Review Django documentation: https://docs.djangoproject.com/
- Contact your system administrator

---

**Built with Django 5.1.6 and Material Dashboard**
