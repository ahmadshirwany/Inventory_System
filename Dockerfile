FROM python:3.11

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create media directory
RUN mkdir -p core/media/profile_pictures

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose port
EXPOSE 5005

# Run migrations and start gunicorn
CMD python manage.py migrate && gunicorn --config gunicorn-cfg.py core.wsgi

