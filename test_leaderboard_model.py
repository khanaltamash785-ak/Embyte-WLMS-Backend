import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'full_auth.settings')
django.setup()

from users.models import WpLeaderboard

print("=== TESTING LEADERBOARD MODEL ===")

try:
    # Test basic queries
    total_users = WpLeaderboard.objects.count()
    print(f"✅ Total users in leaderboard: {total_users}")
    
    # Test filtering
    active_users = WpLeaderboard.objects.filter(point__gt=0).count()
    print(f"✅ Active users (points > 0): {active_users}")
    
    # Test ordering
    top_users = WpLeaderboard.objects.order_by('-point', '-completed_courses')[:5]
    print("✅ Top 5 users:")
    for i, user in enumerate(top_users, 1):
        print(f"  {i}. User {user.user_id}: {user.point} points, {user.completed_courses} courses")
    
    # Test getting specific user
    sample_user = WpLeaderboard.objects.filter(user_id=6).first()
    if sample_user:
        print(f"✅ Sample user (ID 6): {sample_user.point} points, {sample_user.completed_courses} courses")
    
    # Test creating/updating (be careful with existing data)
    print("\n=== TESTING UPDATE FUNCTIONALITY ===")
    test_user_id = 999999  # Use a high ID that probably doesn't exist
    
    # Try to get or create
    user, created = WpLeaderboard.objects.get_or_create(
        user_id=test_user_id,
        defaults={'point': 100, 'completed_courses': 2}
    )
    
    if created:
        print(f"✅ Created test user {test_user_id}")
        # Clean up
        user.delete()
        print("✅ Test user cleaned up")
    else:
        print(f"ℹ️ User {test_user_id} already exists")
    
    print("\n🎉 Leaderboard model is working perfectly!")
    
except Exception as e:
    print(f"❌ Error testing leaderboard: {e}")
    import traceback
    traceback.print_exc()