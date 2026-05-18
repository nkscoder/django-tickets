from django import forms

from .models import Ticket


class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = [
            "title",
            "description",
            "assigned_users",
            "assigned_departments",
            "status",
            "link_type",
            "link_id",
            "link_label",
            "file_no",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }
