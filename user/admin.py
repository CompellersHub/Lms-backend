from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.models import User, Group
from .models import *
from allauth.socialaccount.models import SocialAccount
from unfold.admin import ModelAdmin






try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass



@admin.register(CustomUser)
class UserAdmin(ModelAdmin):
    list_display = ['username', 'email', 'role', 'is_staff', 'is_active']
    list_filter = ['role']

    def has_social_accounts(self, obj):
        return SocialAccount.objects.filter(user=obj).exists()

    has_social_accounts.boolean = True
    has_social_accounts.short_description = 'Linked Social Accounts'

@admin.register(TeacherProfile)
class TeacherAdmin(ModelAdmin):
    list_display = ['user', 'course_taken', 'bio', 'profile_picture']