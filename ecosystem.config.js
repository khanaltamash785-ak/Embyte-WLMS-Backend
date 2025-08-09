module.exports = {
  apps: [
    {
      name: "django_app",
      script: "/var/www/django/venv/bin/gunicorn",
      args: "full_auth.wsgi:application --bind 127.0.0.1:8000",
      cwd: "/var/www/django",
      interpreter: "none",
      env: {
        DJANGO_SETTINGS_MODULE: "full_auth.settings",
        PYTHONPATH: "/var/www/django",
      }
    }
  ]
};
