from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http import JsonResponse
from rest_framework import filters, generics, permissions

from tickets.conf import user_search_fields
from tickets.views.decorators import ticket_login_required

from ..models import Question
from ..serializers import TicketCreateSerializer, UserSerializer


User = get_user_model()


class UserSearchAPIView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = user_search_fields()

    def get_queryset(self):
        return User.objects.filter(is_active=True).order_by("id")


class TicketCreateAPIView(generics.CreateAPIView):
    serializer_class = TicketCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


@ticket_login_required
def get_questions_by_category(request):
    category_id = request.GET.get("category_id")
    questions = []
    if category_id:
        questions = list(
            Question.objects.filter(category_id=category_id, status="active").values(
                "id", "text"
            )
        )
    return JsonResponse({"questions": questions})


@ticket_login_required
def get_users_by_query(request):
    """Optional JSON user picker for create forms."""
    q = request.GET.get("q", "").strip()
    qs = User.objects.filter(is_active=True)
    if q:
        flt = Q()
        for field in user_search_fields():
            flt |= Q(**{f"{field}__icontains": q})
        qs = qs.filter(flt)
    data = [
        {"id": u.id, "label": f"{u}"}
        for u in qs.order_by("id")[:50]
    ]
    return JsonResponse({"users": data})
