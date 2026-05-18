from django.contrib import admin
from django.contrib.auth import get_user_model

from .models import (
    Category,
    Department,
    HintAnswer,
    Question,
    ReportSummary,
    Signater,
    Ticket,
    TicketAnswer,
    TicketLog,
    TicketNotification,
    TicketReassignment,
    TicketSignater,
    TicketStatusHistory,
)

User = get_user_model()


class HintAnswerInline(admin.TabularInline):
    model = HintAnswer
    extra = 1


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "text", "status", "category", "created_at")
    list_filter = ("status", "category")
    search_fields = ("text",)
    inlines = [HintAnswerInline]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "created_at")
    search_fields = ("name",)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "created_by", "status", "link_type", "created_at")
    list_filter = ("status", "link_type", "is_deleted", "created_at")
    search_fields = ("title", "description", "link_label", "file_no")
    filter_horizontal = ("assigned_users", "assigned_departments")
    raw_id_fields = ("created_by", "closed_by", "signater")


@admin.register(TicketLog)
class TicketLogAdmin(admin.ModelAdmin):
    list_display = ("id", "ticket", "user", "created_at")
    search_fields = ("message",)


@admin.register(TicketReassignment)
class TicketReassignmentAdmin(admin.ModelAdmin):
    list_display = ("id", "ticket", "reassigned_by", "created_at")
    filter_horizontal = ("new_assigned_users",)


@admin.register(TicketStatusHistory)
class TicketStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("ticket", "old_status", "new_status", "changed_by", "created_at")


@admin.register(TicketAnswer)
class TicketAnswerAdmin(admin.ModelAdmin):
    list_display = ("ticket", "question", "answered_by", "is_final", "version")
    list_filter = ("is_final", "is_active")


@admin.register(ReportSummary)
class ReportSummaryAdmin(admin.ModelAdmin):
    list_display = ("ticket", "user", "created_at")


@admin.register(TicketNotification)
class TicketNotificationAdmin(admin.ModelAdmin):
    list_display = ("recipient", "ticket", "notification_type", "is_read", "created_at")
    list_filter = ("is_read", "notification_type")


@admin.register(Signater)
class SignaterAdmin(admin.ModelAdmin):
    list_display = ("id", "ranks", "status")


@admin.register(TicketSignater)
class TicketSignaterAdmin(admin.ModelAdmin):
    list_display = ("ticket", "user", "signater", "action_type")
