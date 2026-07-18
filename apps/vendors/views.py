from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
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
