from rest_framework.exceptions import ValidationError


def org_scoped(queryset, user):
    """
    Scope a queryset to the user's organization.

    - Superusers see everything.
    - Users without an organization see nothing.
    - Everyone else sees only rows belonging to their organization.
    """
    if user.is_superuser:
        return queryset
    if not getattr(user, 'organization_id', None):
        return queryset.none()
    return queryset.filter(organization_id=user.organization_id)


def require_organization(user):
    """Raise a DRF ValidationError when the user has no organization (creates are blocked)."""
    if not getattr(user, 'organization_id', None):
        raise ValidationError('You must belong to an organization to create records.')
    return user.organization_id
