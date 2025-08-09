import os
import django
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'full_auth.settings')

try:
    django.setup()
    print("✅ Django setup successful")
except Exception as e:
    print(f"❌ Django setup failed: {e}")
    sys.exit(1)

from django.db import connection

print("\n=== DATABASE CONNECTION TEST ===")
try:
    with connection.cursor() as cursor:
        # Test basic connection
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        print(f"✅ MySQL Version: {version[0]}")
        
        cursor.execute("SELECT DATABASE()")
        db_name = cursor.fetchone()
        print(f"✅ Current Database: {db_name[0]}")
        
        # Check what tables exist
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        table_names = [table[0] for table in tables]
        print(f"✅ Total Tables: {len(table_names)}")
        
        print("\n=== EXISTING TABLES ===")
        for table_name in sorted(table_names):
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"📋 {table_name}: {count} records")
        
        # Check for Django system tables specifically
        django_tables = [
            'django_migrations',
            'django_content_type',
            'auth_permission',
            'auth_user',
            'django_session',
            'django_admin_log'
        ]
        
        print("\n=== DJANGO SYSTEM TABLES STATUS ===")
        missing_tables = []
        for table in django_tables:
            if table in table_names:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"✅ {table}: {count} records")
            else:
                print(f"❌ {table}: MISSING")
                missing_tables.append(table)
        
        # Check if wp_leaderboard exists and has data
        print("\n=== LEADERBOARD TABLE CHECK ===")
        if 'wp_leaderboard' in table_names:
            cursor.execute("DESCRIBE wp_leaderboard")
            columns = cursor.fetchall()
            print("wp_leaderboard structure:")
            for column in columns:
                print(f"  - {column[0]} ({column[1]})")
            
            cursor.execute("SELECT COUNT(*) FROM wp_leaderboard")
            count = cursor.fetchone()[0]
            print(f"✅ wp_leaderboard has {count} records")
            
            if count > 0:
                cursor.execute("SELECT * FROM wp_leaderboard LIMIT 3")
                sample_data = cursor.fetchall()
                print("Sample data:")
                for row in sample_data:
                    print(f"  {row}")
        else:
            print("❌ wp_leaderboard table not found")
        
        print(f"\n=== SUMMARY ===")
        print(f"✅ Database connection: SUCCESS")
        print(f"📊 Total tables: {len(table_names)}")
        print(f"❌ Missing Django tables: {len(missing_tables)}")
        if missing_tables:
            print(f"Missing: {', '.join(missing_tables)}")
            
except Exception as e:
    print(f"❌ Database connection failed: {e}")
    import traceback
    traceback.print_exc()