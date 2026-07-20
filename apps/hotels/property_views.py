from rest_framework import status
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.orgs import org_scoped, require_organization
from apps.core.permissions import IsAdminRole

from .property_filters import HotelPropertyFilter
from .property_models import HotelProperty
from .property_serializers import HotelPropertySerializer


class HotelPropertyListCreateView(ListCreateAPIView):
    serializer_class = HotelPropertySerializer
    filterset_class = HotelPropertyFilter
    search_fields = ['name', 'address', 'phone']
    ordering_fields = ['name', 'created_at']

    def get_queryset(self):
        return org_scoped(
            HotelProperty.objects.select_related('created_by'),
            self.request.user,
        )

    def perform_create(self, serializer):
        require_organization(self.request.user)
        serializer.save(
            created_by=self.request.user,
            organization_id=self.request.user.organization_id,
        )


class HotelPropertyDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = HotelPropertySerializer

    def get_queryset(self):
        return org_scoped(
            HotelProperty.objects.select_related('created_by'),
            self.request.user,
        )

    def get_permissions(self):
        if self.request.method == 'DELETE':
            return [IsAdminRole()]
        return [IsAuthenticated()]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.bookings.exists():
            return Response(
                {
                    'detail': (
                        'This hotel cannot be deleted because it is linked to '
                        'one or more bookings.'
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)
