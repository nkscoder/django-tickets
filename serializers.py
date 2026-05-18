from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Ticket

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "first_name", "last_name", "email", "username"]
        extra_kwargs = {
            "first_name": {"required": False},
            "last_name": {"required": False},
            "email": {"required": False},
            "username": {"required": False},
        }


class TicketCreateSerializer(serializers.ModelSerializer):
    assignee_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )
    question_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )

    class Meta:
        model = Ticket
        fields = [
            "title",
            "description",
            "link_type",
            "link_id",
            "link_label",
            "file_no",
            "assignee_ids",
            "question_ids",
        ]

    def create(self, validated_data):
        assignee_ids = validated_data.pop("assignee_ids", [])
        question_ids = validated_data.pop("question_ids", [])
        request = self.context.get("request")
        user = request.user if request else None

        ticket = Ticket.objects.create(created_by=user, **validated_data)

        from .models import Question, TicketAnswer

        for uid in assignee_ids:
            try:
                assignee = User.objects.get(pk=uid)
            except User.DoesNotExist:
                continue
            ticket.assigned_users.add(assignee)
            for qid in question_ids:
                try:
                    question = Question.objects.get(pk=qid)
                except Question.DoesNotExist:
                    continue
                TicketAnswer.objects.get_or_create(
                    ticket=ticket,
                    question=question,
                    answered_by=assignee,
                )
        return ticket
