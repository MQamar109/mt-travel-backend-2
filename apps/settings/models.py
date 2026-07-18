from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class UserSettings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='settings')
    
    # Settings stored as JSON:
    # {
    #   "currency": "PKR",
    #   "tabs": {
    #     "vendor": { "currentView": "table" },
    #     "ticket": { "sections": { "section_name": true } },
    #     "hotel": { "currentView": "table", "sections": { "section_name": true } }
    #   }
    # }
    data = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "User Settings"

    def __str__(self):
        return f"Settings for {self.user.email}"
