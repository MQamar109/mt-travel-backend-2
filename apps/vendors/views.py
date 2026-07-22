from django.db.models.deletion import ProtectedError
from rest_framework import status
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.core.permissions import IsAdminRole
from apps.core.orgs import org_scoped, require_organization
from .models import Vendor
from .serializers import VendorSerializer
from .filters import VendorFilter

class VendorListCreateView(ListCreateAPIView):
    serializer_class = VendorSerializer
    filterset_class = VendorFilter
    search_fields = ['name', 'company', 'short_name', 'email']
    ordering_fields = ['name', 'created_at']

    def get_queryset(self):
        return org_scoped(Vendor.objects.select_related('created_by'), self.request.user)

    def perform_create(self, serializer):
        require_organization(self.request.user)
        serializer.save(created_by=self.request.user, organization_id=self.request.user.organization_id)


class VendorDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = VendorSerializer

    def get_queryset(self):
        return org_scoped(Vendor.objects.select_related('created_by'), self.request.user)

    def get_permissions(self):
        if self.request.method == 'DELETE':
            return [IsAdminRole()]
        return [IsAuthenticated()]

    def destroy(self, request, *args, **kwargs):
        vendor = self.get_object()
        linked = []
        for rel_name, label in (
            ('tickets', 'ticket'),
            ('hotels', 'hotel booking'),
            ('visas', 'visa'),
            ('passports', 'passport'),
        ):
            count = getattr(vendor, rel_name).count()
            if count:
                linked.append(f'{count} {label}{"" if count == 1 else "s"}')
        if linked:
            return Response(
                {
                    'detail': (
                        'Cannot delete this vendor because it is used by '
                        + ', '.join(linked)
                        + '. Delete or reassign those records first, or mark the vendor inactive.'
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {'detail': 'Cannot delete this vendor because it is still referenced by other records.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
