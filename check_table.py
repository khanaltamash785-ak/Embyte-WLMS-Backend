import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'full_auth.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("DESCRIBE wp_leaderboard")
    columns = cursor.fetchall()
    print("wp_leaderboard table structure:")
    for column in columns:
        print(f"  {column[0]} - {column[1]} - {column[2]} - {column[3]} - {column[4]} - {column[5]}")