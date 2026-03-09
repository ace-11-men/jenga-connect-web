import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import Profile, HardwareStore, Product, CommissionSetting

# Set up some commissions
print("Creating commissions...")
CommissionSetting.objects.get_or_create(category='cement', unit='bag', defaults={'commission_per_unit': 500})
CommissionSetting.objects.get_or_create(category='building_blocks', unit='piece', defaults={'commission_per_unit': 50})
CommissionSetting.objects.get_or_create(category='iron_rods', unit='bar', defaults={'commission_per_unit': 1000})

print("Creating hardware stores and products...")
# Shop 1
if not User.objects.filter(username='0711111111').exists():
    user1 = User.objects.create_user(username='0711111111', password='password123')
    pf1 = Profile.objects.create(user=user1, phone='0711111111', role='hardware', full_name='Arusha Prime Suppliers', area='Arusha CBD')
    st1 = HardwareStore.objects.create(owner=pf1, name='Arusha Prime Suppliers', area='Arusha CBD')
    
    Product.objects.create(store=st1, category='cement', name='Simba Cement 42.5R', hardware_price_per_unit=16500, unit='bag', delivery_eta_hours=24)
    Product.objects.create(store=st1, category='iron_rods', name='12mm Twisted Iron Bars', hardware_price_per_unit=24500, unit='bar', delivery_eta_hours=48)

# Shop 2
if not User.objects.filter(username='0722222222').exists():
    user2 = User.objects.create_user(username='0722222222', password='password123')
    pf2 = Profile.objects.create(user=user2, phone='0722222222', role='hardware', full_name='Mianzini Builders Hub', area='Mianzini')
    st2 = HardwareStore.objects.create(owner=pf2, name='Mianzini Builders Hub', area='Mianzini')
    
    Product.objects.create(store=st2, category='cement', name='Twiga Cement 32.5N', hardware_price_per_unit=15000, unit='bag', delivery_eta_hours=12)
    Product.objects.create(store=st2, category='building_blocks', name='Solid Concrete Blocks 6"', hardware_price_per_unit=1200, unit='piece', stock_units=5000)

print("Database seeded successfully.")
