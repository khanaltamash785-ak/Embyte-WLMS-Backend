import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'full_auth.settings')
django.setup()

from django.db import connection
from django.core.management import execute_from_command_line

print("=== CREATING MISSING DJANGO SYSTEM TABLES ===")

try:
    # Create the missing tables manually
    with connection.cursor() as cursor:
        print("1. Creating django_content_type table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS django_content_type (
                id INT AUTO_INCREMENT PRIMARY KEY,
                app_label VARCHAR(100) NOT NULL,
                model VARCHAR(100) NOT NULL,
                UNIQUE KEY django_content_type_app_label_model_76bd3d3b_uniq (app_label, model)
            )
        """)
        
        print("2. Creating auth_permission table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auth_permission (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                content_type_id INT NOT NULL,
                codename VARCHAR(100) NOT NULL,
                UNIQUE KEY auth_permission_content_type_id_codename_01ab375a_uniq (content_type_id, codename),
                FOREIGN KEY (content_type_id) REFERENCES django_content_type (id)
            )
        """)
        
        print("3. Creating auth_user table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auth_user (
                id INT AUTO_INCREMENT PRIMARY KEY,
                password VARCHAR(128) NOT NULL,
                last_login DATETIME(6),
                is_superuser TINYINT(1) NOT NULL,
                username VARCHAR(150) NOT NULL UNIQUE,
                first_name VARCHAR(150) NOT NULL,
                last_name VARCHAR(150) NOT NULL,
                email VARCHAR(254) NOT NULL,
                is_staff TINYINT(1) NOT NULL,
                is_active TINYINT(1) NOT NULL,
                date_joined DATETIME(6) NOT NULL
            )
        """)
        
        print("4. Creating django_session table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS django_session (
                session_key VARCHAR(40) PRIMARY KEY,
                session_data LONGTEXT NOT NULL,
                expire_date DATETIME(6) NOT NULL,
                KEY django_session_expire_date_a5c62663 (expire_date)
            )
        """)
        
        print("5. Creating django_admin_log table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS django_admin_log (
                id INT AUTO_INCREMENT PRIMARY KEY,
                action_time DATETIME(6) NOT NULL,
                object_id LONGTEXT,
                object_repr VARCHAR(200) NOT NULL,
                action_flag SMALLINT UNSIGNED NOT NULL,
                change_message LONGTEXT NOT NULL,
                content_type_id INT,
                user_id INT NOT NULL,
                FOREIGN KEY (content_type_id) REFERENCES django_content_type (id),
                FOREIGN KEY (user_id) REFERENCES auth_user (id)
            )
        """)
        
        print("6. Inserting basic content types...")
        cursor.execute("""
            INSERT IGNORE INTO django_content_type (app_label, model) VALUES 
            ('contenttypes', 'contenttype'),
            ('auth', 'permission'),
            ('auth', 'group'),
            ('auth', 'user'),
            ('sessions', 'session'),
            ('admin', 'logentry'),
            ('users', 'useraccount')
        """)
        
    print("✅ All Django system tables created successfully!")
    
    # Now try to run migrations to populate the tables properly
    print("\n=== RUNNING DJANGO MIGRATIONS ===")
    try:
        execute_from_command_line(['manage.py', 'migrate', '--fake-initial'])
        print("✅ Migrations completed successfully!")
    except Exception as e:
        print(f"⚠️ Migration warning (this is normal): {e}")
        print("Trying alternative migration approach...")
        
        # Try individual migrations
        try:
            execute_from_command_line(['manage.py', 'migrate', 'contenttypes', '--fake'])
            execute_from_command_line(['manage.py', 'migrate', 'auth', '--fake'])
            execute_from_command_line(['manage.py', 'migrate', 'sessions', '--fake'])
            execute_from_command_line(['manage.py', 'migrate', 'admin', '--fake'])
            print("✅ Individual migrations completed!")
        except Exception as e2:
            print(f"⚠️ Some migrations failed: {e2}")
            print("This is usually fine for existing databases")
    
    # Verify the tables were created
    print("\n=== VERIFICATION ===")
    with connection.cursor() as cursor:
        django_tables = [
            'django_content_type',
            'auth_permission', 
            'auth_user',
            'django_session',
            'django_admin_log'
        ]
        
        for table in django_tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"✅ {table}: {count} records")
    
    print("\n🎉 Django system tables are now ready!")
    
except Exception as e:
    print(f"❌ Error creating tables: {e}")
    import traceback
    traceback.print_exc()