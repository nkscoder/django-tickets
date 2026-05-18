"""Layer A — generic ticket system models (no host-project coupling)."""

from django.conf import settings
from django.db import models
from django.utils import timezone


class Department(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class TicketQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_deleted=False)

    def deleted(self):
        return self.filter(is_deleted=True)

    def soft_delete(self, user=None):
        return self.update(
            is_deleted=True,
            deleted_at=timezone.now(),
            deleted_by=user,
        )

    def restore(self):
        return self.update(
            is_deleted=False,
            deleted_at=None,
            deleted_by=None,
        )


class ActiveTicketManager(models.Manager):
    def get_queryset(self):
        return TicketQuerySet(self.model, using=self._db).active()


class AllTicketManager(models.Manager):
    def get_queryset(self):
        return TicketQuerySet(self.model, using=self._db)


class Ticket(models.Model):
    STATUS_CHOICES = [
        ("open", "Open"),
        ("assigned", "Assigned"),
        ("closed", "Closed"),
        ("reopened", "Reopened"),
        ("submitted", "Submitted"),
        ("reassigned", "Reassigned"),
    ]

    title = models.CharField(max_length=255)
    is_final = models.BooleanField(default=False)
    description = models.TextField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="tickets_created",
        on_delete=models.CASCADE,
    )
    assigned_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="assigned_tickets",
        blank=True,
    )
    assigned_departments = models.ManyToManyField(Department, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    request_type = models.CharField(max_length=255, null=True, blank=True)

    # Generic link to an external record (type + id + optional JSON snapshot)
    link_type = models.CharField(max_length=64, blank=True, default="generic", db_index=True)
    link_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    link_label = models.CharField(max_length=512, null=True, blank=True)
    extra_data = models.JSONField(null=True, blank=True)

    # Optional aliases for older databases (synced in save())
    models_name = models.CharField(max_length=255, blank=True, default="generic", db_index=True)
    models_id = models.CharField(max_length=255, null=True, blank=True)
    models_object = models.JSONField(null=True, blank=True)

    reference_code = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    file_no = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    external_file_no = models.CharField(max_length=100, null=True, blank=True, db_index=True)

    rcn = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    mha_file_no = models.CharField(max_length=100, null=True, blank=True, db_index=True)

    signater = models.ForeignKey(
        "Signater",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets",
    )

    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tickets_deleted",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="tickets_closed",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    objects = ActiveTicketManager()
    all_objects = AllTicketManager()

    def save(self, *args, **kwargs):
        if self.link_type and not self.models_name:
            self.models_name = self.link_type
        if self.link_id and not self.models_id:
            self.models_id = self.link_id
        if self.link_label and self.models_object is None:
            self.models_object = {"label": self.link_label}
        if self.reference_code and not self.rcn:
            self.rcn = self.reference_code
        if self.external_file_no and not self.mha_file_no:
            self.mha_file_no = self.external_file_no
        super().save(*args, **kwargs)

    def soft_delete(self, user=None, save=True):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        if save:
            self.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])

    def restore(self, save=True):
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        if save:
            self.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])

    def __str__(self):
        return f"{self.title} ({self.status}) (#{self.id})"

    class Meta:
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_by"]),
            models.Index(fields=["link_type"]),
            models.Index(fields=["link_id"]),
            models.Index(fields=["is_deleted", "created_at"]),
            models.Index(fields=["is_deleted", "status"]),
        ]


class TicketLog(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="logs")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name="ticket_logs_received",
        on_delete=models.CASCADE,
    )
    ticketReassignment = models.ForeignKey(
        "TicketReassignment",
        related_name="reassignment_logs",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class TicketReassignment(models.Model):
    ticket = models.ForeignKey(Ticket, related_name="reassignments", on_delete=models.CASCADE)
    is_final = models.BooleanField(default=False)
    reassigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="reassigned_tickets",
        on_delete=models.CASCADE,
    )
    new_assigned_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="reassignment_targets",
    )
    reason = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Reassignment #{self.id} on ticket #{self.ticket_id}"


class TicketStatusHistory(models.Model):
    ticket = models.ForeignKey("Ticket", related_name="status_history", on_delete=models.CASCADE)
    old_status = models.CharField(
        max_length=20, choices=Ticket.STATUS_CHOICES, null=True, blank=True
    )
    new_status = models.CharField(max_length=20, choices=Ticket.STATUS_CHOICES)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["ticket"])]
        ordering = ["created_at"]


class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Question(models.Model):
    STATUS_CHOICES = (("active", "Active"), ("inactive", "Inactive"))

    text = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="questions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.text[:50]


class HintAnswer(models.Model):
    STATUS_CHOICES = (("active", "Active"), ("inactive", "Inactive"))

    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="hint_answers"
    )
    hint_answer = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class TicketAnswer(models.Model):
    ticket = models.ForeignKey(Ticket, related_name="answers", on_delete=models.CASCADE)
    question = models.ForeignKey(Question, related_name="answers", on_delete=models.CASCADE)
    answer = models.TextField(blank=True, null=True)
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    is_final = models.BooleanField(default=False)
    answered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="ticket_answers",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (
            "ticket",
            "question",
            "is_active",
            "is_final",
            "answered_by",
            "version",
        )


class ReassignmentAnswer(models.Model):
    reassignment = models.ForeignKey(
        TicketReassignment, related_name="answers", on_delete=models.CASCADE
    )
    question = models.ForeignKey(
        Question, related_name="reassignment_answers", on_delete=models.CASCADE
    )
    answer = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_final = models.BooleanField(default=False)
    answered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="reassignment_answers",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("reassignment", "is_active", "is_final", "question", "answered_by")


class TicketQuestionHistory(models.Model):
    ticket_answer = models.ForeignKey("TicketAnswer", on_delete=models.CASCADE)
    old_answer = models.TextField(blank=True, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    reason = models.TextField(blank=True, null=True)


class FileUpload(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="uploads")
    reassignment = models.ForeignKey(
        TicketReassignment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reassigned_uploads",
    )
    log = models.ForeignKey(
        "TicketLog",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="file_uploads",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="file_uploads"
    )
    file = models.FileField(upload_to="ticket_uploads/%Y/%m/%d/")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class ReportSummary(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE)
    reassignment = models.ForeignKey(
        TicketReassignment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reassignment_ticket",
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    file = models.FileField(upload_to="ticket_reports/%Y/%m/%d/", blank=True)
    summary = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class TicketNotification(models.Model):
    class NotificationType(models.TextChoices):
        TICKET_ASSIGNED = "ticket_assigned", "Ticket assigned"
        TICKET_CREATED = "ticket_created", "Ticket created"
        TICKET_REASSIGNED = "ticket_reassigned", "Ticket reassigned"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ticket_notifications",
    )
    ticket = models.ForeignKey("Ticket", on_delete=models.CASCADE, related_name="notifications")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ticket_notifications_sent",
    )
    notification_type = models.CharField(
        max_length=40,
        choices=NotificationType.choices,
        default=NotificationType.TICKET_ASSIGNED,
    )
    message = models.TextField()
    is_read = models.BooleanField(default=False, db_index=True)
    meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "ticket_notification"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read", "created_at"]),
            models.Index(fields=["ticket", "created_at"]),
        ]


class TicketActionTrace(models.Model):
    ticket = models.ForeignKey("Ticket", on_delete=models.CASCADE, related_name="action_traces")
    action_key = models.CharField(max_length=100, db_index=True)
    is_success = models.BooleanField(default=False)
    status_text = models.CharField(max_length=255, blank=True, null=True)
    error_text = models.TextField(blank=True, null=True)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    performed_at = models.DateTimeField(auto_now_add=True)
    office_file_no = models.CharField(max_length=150, blank=True, null=True)
    meta = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "ticket_action_trace"
        ordering = ["-performed_at"]


class Signater(models.Model):
    STATUS_CHOICES = (("active", "Active"), ("inactive", "Inactive"))

    ranks = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")

    class Meta:
        db_table = "signater"

    def __str__(self):
        return self.ranks


class TicketSignater(models.Model):
    ticket = models.ForeignKey("Ticket", on_delete=models.CASCADE, related_name="ticket_signaters")
    signater = models.ForeignKey("Signater", on_delete=models.CASCADE, related_name="ticket_signaters")
    action_type = models.CharField(max_length=255, blank=True, null=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ticket_signaters",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ticket_signater"
        constraints = [
            models.UniqueConstraint(
                fields=["ticket", "user", "action_type"],
                name="unique_ticket_user_signater_action_type",
            )
        ]
