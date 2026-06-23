from django.contrib import admin
from .models import Payment, RevenueSplit, Wallet, Payout
admin.site.register(Payment)
admin.site.register(RevenueSplit)
admin.site.register(Wallet)
admin.site.register(Payout)
