from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import UserSettings
from .serializers import UserSettingsSerializer

class UserSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get user settings, creating defaults if missing."""
        settings, created = UserSettings.objects.get_or_create(user=request.user)

        # Initialize with defaults if first time
        if created or not settings.data:
            settings.data = {
                'appMode': 'PKR',
                'vendorView': 'table',
                'ticketView': 'table',
                'ticketStatsOpen': True,
                'hotelView': 'table',
                'hotelStatsOpen': True,
                'tabs': {
                    'ticket': {'sections': {}},
                    'hotel': {'sections': {}},
                }
            }
            settings.save()

        serializer = UserSettingsSerializer(settings)
        return Response(serializer.data)

    def patch(self, request):
        """Update user settings."""
        settings, created = UserSettings.objects.get_or_create(user=request.user)
        
        # Merge provided data with existing
        if 'data' in request.data:
            settings.data = request.data['data']
        
        settings.save()
        serializer = UserSettingsSerializer(settings)
        return Response(serializer.data)
