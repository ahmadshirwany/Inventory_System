# Security & Environment Setup Guide

## ⚠️ IMPORTANT: Before Pushing to Git

This file contains instructions for securing your deployment and setting up environment variables.

## 🔒 Sensitive Files (Never Commit These!)

The following files contain sensitive information and should **NEVER** be committed to git:

### Already Protected by .gitignore:
- `.env` - Environment variables (credentials, secrets)
- `IP_data.json` - Server IP and passwords
- `db.sqlite3` - Database with user data
- `media/` - User uploaded files
- `*.log` - Log files that may contain sensitive data
- `.venv/` - Virtual environment

### Check Before Committing:
Run this command to verify sensitive files are not tracked:
```bash
git status
```

If you see any of these files, remove them from tracking:
```bash
git rm --cached .env
git rm --cached IP_data.json
git rm --cached db.sqlite3
```

## 🔧 Environment Setup

### 1. Copy Example Files

After cloning the repository, create your configuration files from examples:

```bash
# Copy environment variables template
cp .env.example .env

# Copy IP configuration template
cp IP_data.json.example IP_data.json
```

### 2. Configure .env File

Edit `.env` and set your values:

```env
# Development Settings
DEBUG=True
SECRET_KEY=generate-a-secure-random-key-here

# Production Settings (when deploying)
DEBUG=False
SECRET_KEY=use-a-very-long-random-string-here
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
```

**Generate a secure SECRET_KEY:**
```python
# In Python shell
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
```

Or online: https://djecrety.ir/

### 3. Configure IP_data.json

Edit `IP_data.json` with your server details:

```json
{
  "IP": "your.server.ip.address",
  "Pass": "your-secure-password"
}
```

## 🛡️ Security Checklist Before Going Live

### Pre-Production:
- [ ] Set `DEBUG=False` in `.env`
- [ ] Generate new `SECRET_KEY`
- [ ] Configure `ALLOWED_HOSTS` with your domain
- [ ] Set up HTTPS/SSL certificates
- [ ] Change default database password
- [ ] Update `IP_data.json` with production credentials
- [ ] Enable CSRF protection (already enabled)
- [ ] Configure secure cookies

### Production Settings:

Add these to your `.env` for production:

```env
DEBUG=False
SECRET_KEY=your-very-long-secure-random-key
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Security Settings
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_BROWSER_XSS_FILTER=True
SECURE_CONTENT_TYPE_NOSNIFF=True

# Database (if using PostgreSQL)
DATABASE_URL=postgresql://user:password@localhost:5432/inventory_db
```

## 📝 What's Safe to Commit

### ✅ Safe to commit:
- Source code (*.py, *.html, *.css, *.js)
- Configuration templates (*.example files)
- Documentation (*.md files)
- Requirements (requirements.txt)
- Docker configuration (Dockerfile, docker-compose.yml)
- Static assets (images, CSS, JS)
- Empty directories with .gitkeep
- `.gitignore` file itself

### ❌ Never commit:
- `.env` file (use .env.example instead)
- `IP_data.json` (use IP_data.json.example instead)
- `db.sqlite3` or any database files
- `*.log` files
- `media/` folder with user uploads
- `.venv/` virtual environment
- `__pycache__/` folders
- Personal IDE settings (.vscode/, .idea/)
- Any file with passwords, API keys, or tokens

## 🔍 Verify Before Push

Run this before every `git push`:

```bash
# Check what files will be committed
git status

# Verify .gitignore is working
git check-ignore .env IP_data.json db.sqlite3

# Should show all three files as ignored
```

## 🚨 If You Accidentally Committed Secrets

If you already committed sensitive data:

### 1. Remove from Git History
```bash
# Remove file from current commit
git rm --cached .env
git commit -m "Remove sensitive file"

# If already pushed, you need to remove from history
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env" \
  --prune-empty --tag-name-filter cat -- --all

# Force push (WARNING: This rewrites history)
git push origin --force --all
```

### 2. Rotate All Secrets
- Generate new SECRET_KEY
- Change all passwords
- Regenerate API tokens
- Update IP_data.json credentials

### 3. Consider the Repository Compromised
- If pushed to public repository, assume all secrets are exposed
- Change ALL credentials immediately
- Monitor for unauthorized access

## 📚 Additional Security Resources

- Django Security: https://docs.djangoproject.com/en/stable/topics/security/
- OWASP Top 10: https://owasp.org/www-project-top-ten/
- Git Security: https://git-scm.com/book/en/v2/Git-Tools-Credential-Storage

## 🔐 Password Security Best Practices

1. **Never** hardcode passwords in code
2. Use environment variables for all secrets
3. Use strong, unique passwords (20+ characters)
4. Enable two-factor authentication on git hosting
5. Rotate credentials regularly
6. Use password managers for storing credentials
7. Don't share credentials via email or chat

## 📞 Support

If you have questions about security:
- Review Django security documentation
- Consult with your system administrator
- Perform security audit before production deployment

---

**Last Updated**: January 29, 2026
**Remember**: Security is not optional. Protect your users' data!
