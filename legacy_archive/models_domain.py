from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone
import uuid

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
            deleted_by=user
        )

    def restore(self):
        return self.update(
            is_deleted=False,
            deleted_at=None,
            deleted_by=None
        )


class ActiveTicketManager(models.Manager):
    def get_queryset(self):
        return TicketQuerySet(self.model, using=self._db).active()


class AllTicketManager(models.Manager):
    def get_queryset(self):
        return TicketQuerySet(self.model, using=self._db)
        
class Ticket(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('assigned', 'Assigned'),
        ('closed', 'Closed'),
        ('reopened', 'Reopened'),
        ('submitted', 'Submitted'),
    ]
    MODELS_CHOICES = [
        ('ngo', 'NGO'),
        ('str', 'STR'),
        ('spyder', 'Sypder'),
        ('cms', 'CMS'),
    ]

    title = models.CharField(max_length=255)
    is_final = models.BooleanField(default=False)
    description = models.TextField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='tickets_created', on_delete=models.CASCADE)
    assigned_users = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='assigned_tickets', blank=True)
    assigned_departments = models.ManyToManyField(Department, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    request_type = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    closed_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='tickets_closed', on_delete=models.SET_NULL, null=True, blank=True)
    models_name = models.CharField(max_length=255, choices=MODELS_CHOICES, default='ngo')
    models_id = models.CharField(max_length=255, null=True, blank=True)
    models_object = models.JSONField(null=True, blank=True)
    rcn = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    file_no = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    mha_file_no = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    signater = models.ForeignKey(
        "Signater",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets"
    )
    # # soft delete
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="tickets_deleted"
    )

    objects = ActiveTicketManager()
    all_objects = AllTicketManager()

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
        return f"{self.title} ({self.status}) ({self.id})"
    class Meta:
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_by"]),
            models.Index(fields=["models_name"]),
            models.Index(fields=["models_id"]),
            models.Index(fields=["is_deleted", "created_at"]),
            models.Index(fields=["is_deleted", "status"]),
            models.Index(fields=["is_deleted", "created_by"]),
        ]





class TicketLog(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)  # from_user
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name="ticket_logs_received",
        on_delete=models.CASCADE,
    )
    ticketReassignment = models.ForeignKey("TicketReassignment", related_name='reassignment_logs', on_delete=models.CASCADE, null=True, blank=True)
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class TicketReassignment(models.Model):
    ticket = models.ForeignKey(Ticket, related_name='reassignments', on_delete=models.CASCADE)
    is_final = models.BooleanField(default=False)
    reassigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='reassigned_tickets', on_delete=models.CASCADE)
    new_assigned_users = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='reassignment_targets')
    reason = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Reassignment of {self.ticket.title} by {self.reassigned_by} on {self.created_at}"

class TicketStatusHistory(models.Model):
    ticket = models.ForeignKey('Ticket',related_name='status_history',on_delete=models.CASCADE)
    old_status = models.CharField( max_length=20, choices=Ticket.STATUS_CHOICES,  null=True,  blank=True )
    new_status = models.CharField(max_length=20,choices=Ticket.STATUS_CHOICES)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['ticket']),
        ]
        ordering = ['created_at']
        verbose_name = "Ticket Status History"
        verbose_name_plural = "Ticket Status Histories"

    def __str__(self):
        return f"Ticket {self.ticket.id}: {self.old_status} → {self.new_status} by {self.changed_by}"


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
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    )
    text = models.TextField()  
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='questions') 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)       # only auto_now

    def __str__(self):
        return self.text[:50]  # Show first 50 chars in admin


class HintAnswer(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    )

    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="hint_answers"
    )
    hint_answer = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)   # only auto_now_add
    updated_at = models.DateTimeField(auto_now=True)       # only auto_now

    def __str__(self):
        return f"Hint for Q{self.question.id}: {self.hint_answer[:40]}"



class TicketAnswer(models.Model):
    ticket = models.ForeignKey(Ticket, related_name='answers', on_delete=models.CASCADE)
    question = models.ForeignKey(Question, related_name='answers', on_delete=models.CASCADE)
    answer = models.TextField(blank=True, null=True)
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    is_final = models.BooleanField(default=False)
    answered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='ticket_answers',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('ticket', 'question',"is_active", "is_final", 'answered_by', 'version')
    def __str__(self):
        return f"Answer to '{self.question}' for Ticket {self.ticket.id}"

 
class ReassignmentAnswer(models.Model):
    reassignment = models.ForeignKey(TicketReassignment, related_name='answers', on_delete=models.CASCADE)
    question = models.ForeignKey(Question, related_name='reassignment_answers', on_delete=models.CASCADE)
    answer = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_final = models.BooleanField(default=False)
    answered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='reassignment_answers',
        on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        unique_together = ('reassignment', "is_active", "is_final",'question','answered_by')

    def __str__(self):
        return f"Reassignment Answer to '{self.question}' for Ticket {self.reassignment.ticket.id}"


class NGOAuthToken(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ngo_tokens"  # ✅ unique
    )
    token = models.TextField()
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class TicketQuestionHistory(models.Model):
    ticket_answer = models.ForeignKey('TicketAnswer', on_delete=models.CASCADE)
    old_answer    = models.TextField(blank=True, null=True)
    changed_at    = models.DateTimeField(auto_now_add=True)
    changed_by    = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True, blank=True)
    reason        = models.TextField(blank=True, null=True)


class FileUpload(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='uploads')
    reassignment = models.ForeignKey(
        TicketReassignment,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reassigned_uploads'
    )
    log = models.ForeignKey(
        'TicketLog',  
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='file_uploads',
        help_text="Link this file upload to a specific ticket log entry"
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='file_uploads')
    file = models.FileField(upload_to='uploads/%Y/%m/%d/')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.ticket} - {self.user}"

    

class ReportSummary(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE)
    reassignment = models.ForeignKey(
        TicketReassignment,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reassignment_ticket'
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    file = models.FileField(upload_to='uploads/%Y/%m/%d/')
    summary = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['-created_at']
    def __str__(self):
        return f"{self.ticket} - {self.user}"
    

class RegistrationsOther(models.Model):
    rcn = models.CharField(max_length=10, blank=True, null=True, db_comment='registration number')
    registration_application_id = models.CharField(max_length=27, blank=True, null=True, db_comment='application Id')
    section_file_number = models.CharField(max_length=19, blank=True, null=True)
    form_submission_date = models.CharField(max_length=50, blank=True, null=True, db_comment='application submission date')
    darpan_id = models.CharField(max_length=17, blank=True, null=True)
    association_name = models.CharField(max_length=100, blank=True, null=True, db_comment='ngo Name\t')
    association_address = models.TextField(blank=True, null=True)
    association_state = models.CharField(max_length=27, blank=True, null=True)
    association_district = models.CharField(max_length=100, blank=True, null=True)
    association_official_telephone = models.CharField(max_length=30, blank=True, null=True)
    association_email = models.CharField(max_length=52, blank=True, null=True)
    association_official_website = models.CharField(max_length=100, blank=True, null=True)
    association_chief_functionary_phone_number = models.CharField(max_length=42, blank=True, null=True)
    association_chief_functionary_mobile_number = models.CharField(max_length=43, blank=True, null=True)
    act_registration_name = models.CharField(max_length=148, blank=True, null=True)
    act_registration_number = models.CharField(max_length=52, blank=True, null=True)
    date_of_act_registration = models.CharField(max_length=100, blank=True, null=True)
    place_of_act_registration = models.CharField(max_length=149, blank=True, null=True)
    association_pan = models.CharField(max_length=11, blank=True, null=True)
    association_nature = models.CharField(max_length=46, blank=True, null=True)
    bank_name = models.CharField(max_length=44, blank=True, null=True)
    bank_address = models.CharField(max_length=150, blank=True, null=True)
    bank_email = models.CharField(max_length=56, blank=True, null=True)
    ifsc_code = models.CharField(max_length=100, blank=True, null=True)
    account_number = models.CharField(max_length=32, blank=True, null=True)
    association_status = models.CharField(max_length=50, blank=True, null=True)
    cancel_suspended_date = models.CharField(max_length=26, blank=True, null=True)
    cancelled_suspended_remark = models.CharField(max_length=651, blank=True, null=True)
    cancellation_reason = models.CharField(max_length=19, blank=True, null=True)
    registration_certificate_location = models.CharField(max_length=33, blank=True, null=True)
    registration_applications_documents_location = models.CharField(max_length=44, blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()


class Registrations(models.Model):
    rcn = models.CharField(max_length=10, blank=True, null=True, db_comment='registration number')
    registration_application_id = models.CharField(max_length=27, blank=True, null=True, db_comment='application Id')
    section_file_number = models.CharField(max_length=19, blank=True, null=True)
    form_submission_date = models.CharField(max_length=50, blank=True, null=True, db_comment='application submission date')
    darpan_id = models.CharField(max_length=17, blank=True, null=True)
    association_name = models.CharField(max_length=100, blank=True, null=True, db_comment='ngo Name\t')
    association_address = models.TextField(blank=True, null=True)
    association_state = models.CharField(max_length=27, blank=True, null=True)
    association_district = models.CharField(max_length=100, blank=True, null=True)
    association_official_telephone = models.CharField(max_length=30, blank=True, null=True)
    association_email = models.CharField(max_length=52, blank=True, null=True)
    association_official_website = models.CharField(max_length=100, blank=True, null=True)
    association_chief_functionary_phone_number = models.CharField(max_length=42, blank=True, null=True)
    association_chief_functionary_mobile_number = models.CharField(max_length=43, blank=True, null=True)
    act_registration_name = models.CharField(max_length=148, blank=True, null=True)
    act_registration_number = models.CharField(max_length=52, blank=True, null=True)
    date_of_act_registration = models.CharField(max_length=100, blank=True, null=True)
    place_of_act_registration = models.CharField(max_length=149, blank=True, null=True)
    association_pan = models.CharField(max_length=11, blank=True, null=True)
    association_nature = models.CharField(max_length=46, blank=True, null=True)
    bank_name = models.CharField(max_length=44, blank=True, null=True)
    bank_address = models.CharField(max_length=150, blank=True, null=True)
    bank_email = models.CharField(max_length=56, blank=True, null=True)
    ifsc_code = models.CharField(max_length=100, blank=True, null=True)
    account_number = models.CharField(max_length=32, blank=True, null=True)
    association_status = models.CharField(max_length=50, blank=True, null=True)
    cancel_suspended_date = models.CharField(max_length=26, blank=True, null=True)
    cancelled_suspended_remark = models.CharField(max_length=651, blank=True, null=True)
    cancellation_reason = models.CharField(max_length=19, blank=True, null=True)
    registration_certificate_location = models.CharField(max_length=33, blank=True, null=True)
    registration_applications_documents_location = models.CharField(max_length=44, blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'registrations'



class OtherServicesDocumentsLink(models.Model):
    id = models.BigAutoField(primary_key=True)
    rcn = models.CharField(max_length=50, blank=True, null=True)
    registration_application_id = models.CharField(max_length=20, blank=True, null=True)
    section_file_number = models.CharField(max_length=20, blank=True, null=True)
    form_submission_date = models.CharField(max_length=20, blank=True, null=True)
    darpan_id = models.CharField(max_length=20, blank=True, null=True)
    association_name = models.CharField(max_length=100, blank=True, null=True)
    registration_date = models.CharField(max_length=20, blank=True, null=True)
    association_address = models.CharField(max_length=255, blank=True, null=True)
    association_state = models.CharField(max_length=50, blank=True, null=True)
    association_district = models.CharField(max_length=50, blank=True, null=True)
    association_official_telephone = models.TextField(blank=True, null=True)
    email_id = models.CharField(max_length=100, blank=True, null=True)
    association_official_website = models.CharField(max_length=100, blank=True, null=True)
    association_chief_functionary_phone_number = models.TextField(blank=True, null=True)
    association_chief_functionary_mobile_number = models.TextField(blank=True, null=True)
    act_registration_name = models.TextField(blank=True, null=True)
    act_registration_number = models.TextField(blank=True, null=True)
    date_of_act_registration = models.TextField(blank=True, null=True)
    place_of_act_registration = models.TextField(blank=True, null=True)
    pan_number = models.TextField(blank=True, null=True)
    nature_of_association = models.TextField(blank=True, null=True)
    religion = models.CharField(max_length=50, blank=True, null=True)
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    bank_address = models.CharField(max_length=255, blank=True, null=True)
    bank_email_id = models.CharField(max_length=100, blank=True, null=True)
    ifsc_code = models.TextField(blank=True, null=True)
    account_number = models.TextField(blank=True, null=True)
    association_status = models.TextField(blank=True, null=True)
    cancelled_suspended_date = models.CharField(max_length=20, blank=True, null=True)
    cancelled_suspended_remarks = models.TextField(blank=True, null=True)
    cancellation_reason = models.TextField(blank=True, null=True)
    registration_certificate_location = models.CharField(max_length=255, blank=True, null=True)
    registration_applications_documents_location = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'other_services_documents_link'




class OtherServicesDocumentsLink_logs(models.Model):
    id = models.BigAutoField(primary_key=True)
    rcn = models.CharField(max_length=50, blank=True, null=True)
    registration_application_id = models.CharField(max_length=20, blank=True, null=True)
    section_file_number = models.CharField(max_length=20, blank=True, null=True)
    form_submission_date = models.CharField(max_length=20, blank=True, null=True)
    darpan_id = models.CharField(max_length=20, blank=True, null=True)
    association_name = models.CharField(max_length=100, blank=True, null=True)
    registration_date = models.CharField(max_length=20, blank=True, null=True)
    association_address = models.CharField(max_length=255, blank=True, null=True)
    association_state = models.CharField(max_length=50, blank=True, null=True)
    association_district = models.CharField(max_length=50, blank=True, null=True)
    association_official_telephone = models.TextField(blank=True, null=True)
    email_id = models.CharField(max_length=100, blank=True, null=True)
    association_official_website = models.CharField(max_length=100, blank=True, null=True)
    association_chief_functionary_phone_number = models.TextField(blank=True, null=True)
    association_chief_functionary_mobile_number = models.TextField(blank=True, null=True)
    act_registration_name = models.TextField(blank=True, null=True)
    act_registration_number = models.TextField(blank=True, null=True)
    date_of_act_registration = models.TextField(blank=True, null=True)
    place_of_act_registration = models.TextField(blank=True, null=True)
    pan_number = models.TextField(blank=True, null=True)
    nature_of_association = models.TextField(blank=True, null=True)
    religion = models.CharField(max_length=50, blank=True, null=True)
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    bank_address = models.CharField(max_length=255, blank=True, null=True)
    bank_email_id = models.CharField(max_length=100, blank=True, null=True)
    ifsc_code = models.TextField(blank=True, null=True)
    account_number = models.TextField(blank=True, null=True)
    association_status = models.TextField(blank=True, null=True)
    cancelled_suspended_date = models.CharField(max_length=20, blank=True, null=True)
    cancelled_suspended_remarks = models.TextField(blank=True, null=True)
    cancellation_reason = models.TextField(blank=True, null=True)
    registration_certificate_location = models.CharField(max_length=255, blank=True, null=True)
    registration_applications_documents_location = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = "other_services_documents_linkraw"
        managed = False

    

class CommitteeMembersData(models.Model):
    id = models.BigAutoField(primary_key=True)

    fcra_registration_no = models.CharField(max_length=50, null=True, blank=True)
    association_name = models.TextField(null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    district = models.CharField(max_length=150, null=True, blank=True)
    member_name = models.CharField(max_length=200, null=True, blank=True)
    father_husband_name = models.CharField(max_length=200, null=True, blank=True)
    nationality = models.CharField(max_length=100, null=True, blank=True)
    occupation = models.CharField(max_length=200, null=True, blank=True)
    post_in_association = models.CharField(max_length=200, null=True, blank=True)
    relationship_with_other_member = models.CharField(max_length=200, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    mobile = models.CharField(max_length=30, null=True, blank=True)
    application_id = models.CharField(max_length=100, null=True, blank=True)
    aadhaar_number = models.CharField(max_length=50, null=True, blank=True)
    pan_no = models.CharField(max_length=20, null=True, blank=True)
    registration_date = models.DateField(null=True, blank=True)
    # created_at = models.DateTimeField(null=True, blank=True)
    # updated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    uniq_hash = models.CharField(max_length=32, null=True, blank=True, unique=True)

    class Meta:
        db_table = "committee_members_data"
        managed = False



class RegistrationApplications(models.Model):
    registration_application_id = models.CharField(max_length=20, null=True, blank=True)
    section_file_number = models.CharField(max_length=20, null=True, blank=True)
    form_submission_date = models.CharField(max_length=20, null=True, blank=True)
    darpan_id = models.CharField(max_length=20, null=True, blank=True)
    association_name = models.CharField(max_length=100, null=True, blank=True)
    registration_date = models.CharField(max_length=20, null=True, blank=True)
    association_address = models.CharField(max_length=255, null=True, blank=True)
    association_state = models.CharField(max_length=50, null=True, blank=True)
    association_district = models.CharField(max_length=50, null=True, blank=True)
    association_official_telephone = models.TextField(null=True, blank=True)
    email_id = models.CharField(max_length=100, null=True, blank=True)
    association_official_website = models.CharField(max_length=100, null=True, blank=True)
    association_chief_functionary_phone_number = models.TextField(null=True, blank=True)
    association_chief_functionary_mobile_number = models.TextField(null=True, blank=True)
    act_registration_name = models.TextField(null=True, blank=True)
    act_registration_number = models.TextField(null=True, blank=True)
    date_of_act_registration = models.TextField(null=True, blank=True)
    place_of_act_registration = models.TextField(null=True, blank=True)
    pan_number = models.CharField(max_length=15, null=True, blank=True)
    nature_of_association = models.TextField(null=True, blank=True)
    religion = models.CharField(max_length=50, null=True, blank=True)
    bank_name = models.CharField(max_length=100, null=True, blank=True)
    bank_address = models.CharField(max_length=255, null=True, blank=True)
    bank_email_id = models.CharField(max_length=100, null=True, blank=True)
    ifsc_code = models.TextField(null=True, blank=True)
    account_number = models.TextField(null=True, blank=True)
    association_status = models.TextField(null=True, blank=True)
    registration_applications_documents_location = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "application_details"
        managed = False  # IMPORTANT if table already exists



class ImportSession(models.Model):
    token = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    kind = models.CharField(max_length=10)  # reg/com/mem/logs
    filename = models.CharField(max_length=255, blank=True, null=True)

    # store validated rows as JSON (Django will use JSONField)
    rows = models.JSONField()

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    expires_at = models.DateTimeField(db_index=True)

    # optional: who created it (recommended)
    user_id = models.IntegerField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = "import_sessions"
        managed = False


class CommitteeDetails(models.Model):
    passport_number = models.CharField(max_length=21, null=True, blank=True)
    whether_indian_origin = models.BooleanField(null=True, blank=True)
    member_name = models.CharField(max_length=56, null=True, blank=True)
    father_husband_name = models.CharField(max_length=50, null=True, blank=True)
    nationality = models.CharField(max_length=50, null=True, blank=True)
    occupation = models.CharField(max_length=100, null=True, blank=True)
    post_in_association = models.CharField(max_length=49, null=True, blank=True)
    relationship_with_other_member = models.CharField(max_length=100, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    address_foreign_country = models.TextField(null=True, blank=True)
    application_id = models.CharField(max_length=17, null=True, blank=True)
    pan_no = models.CharField(max_length=10, null=True, blank=True)
    date_place_of_birth = models.CharField(max_length=150, null=True, blank=True)
    date_from_residing_india = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    email      = models.CharField(max_length=255, null=True, blank=True)
    landline   = models.CharField(max_length=50, null=True, blank=True)
    mobile  = models.CharField(max_length=50, null=True, blank=True)
    uniq_hash = models.CharField(max_length=32, null=True, blank=True, unique=True)
    class Meta:
        db_table = "application_committee_member_details"
        managed = False

        
class UtilizationBnkDetails(models.Model):
    id = models.BigAutoField(primary_key=True)

    fcra_registration_no = models.CharField(max_length=191)
    application_id = models.CharField(max_length=191)
    association_name = models.CharField(max_length=191)

    # In SQL it's varchar(50), so keep as CharField (not DateField)
    registration_date = models.CharField(max_length=50, null=True, blank=True)

    bank_name = models.CharField(max_length=191)
    bank_address = models.TextField()
    account_no = models.CharField(max_length=191)

    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "utilization_bnk_details"
        managed = False  # set True only if Django should manage/migrate this table
    
# from django.db import models

class ImportSyncLogs(models.Model):
    id = models.BigAutoField(primary_key=True)

    # DB column name: type
    type = models.CharField(max_length=100, db_index=True)

    # DB column name: table_name
    table_name = models.CharField(max_length=100, db_index=True)

    # DB column name: file_name
    file_name = models.CharField(max_length=255, null=True, blank=True)

    inserted = models.BigIntegerField(default=0)
    updated = models.BigIntegerField(default=0)
    skipped = models.BigIntegerField(default=0)

    last_sync_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "import_sync_logs"
        managed = False  # ✅ since table already exists


# tickets/models.py
from django.conf import settings
from django.db import models

class TicketApplicationDoc(models.Model):
    other_services_documents_link = models.ForeignKey(
        'OtherServicesDocumentsLink',
        on_delete=models.CASCADE,
        db_column='other_services_documents_link',
        related_name='application_docs',
    )
    file = models.FileField(upload_to='ticket_application_docs/%Y/%m/%d/', blank=True, null=True)
    status = models.CharField(max_length=255, blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by_id = models.PositiveIntegerField(null=True, blank=True)
    ticket_id = models.PositiveIntegerField(null=True, blank=True)
    class Meta:     
        db_table = 'ticket_application_doc'
        managed = True  # you want Django to create it on 'secondary'



class TicketSectionMeta(models.Model):
    SECTION_CHOICES = (
        ("USER_SECTION", "User Section (NGO Query)"),
        ("OFFICE_BEARER", "Office Bearer Query"),
    )

    ticket = models.ForeignKey("Ticket", on_delete=models.CASCADE, related_name="sections")
    section_type = models.CharField(max_length=30, choices=SECTION_CHOICES)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # can store extra info: selected NGO, app_id, etc.
    meta = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "ticket_section_meta"
        unique_together = ("ticket", "section_type")

    def __str__(self):
        return f"{self.ticket_id} - {self.section_type}"

class TicketMemberRow(models.Model):
    SECTION_TYPES = (
        ("NGO", "NGO"),
        ("OFFICE_BEARER", "OFFICE_BEARER"),
    )

    ticket = models.ForeignKey("Ticket", on_delete=models.CASCADE, related_name="member_rows")
    section_type = models.CharField(max_length=30, choices=SECTION_TYPES, db_index=True)
    member_data_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    member_name = models.CharField(max_length=200, null=True, blank=True)
    father_husband_name = models.CharField(max_length=200, null=True, blank=True)
    nationality = models.CharField(max_length=100, null=True, blank=True)
    occupation = models.CharField(max_length=200, null=True, blank=True)
    post_in_association = models.CharField(max_length=200, null=True, blank=True)
    relationship_with_other_member = models.CharField(max_length=200, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    mobile = models.CharField(max_length=30, null=True, blank=True)
    aadhaar_number = models.CharField(max_length=50, null=True, blank=True)
    pan_no = models.CharField(max_length=20, null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ticket_member_row"
        indexes = [
            models.Index(fields=["ticket", "section_type"]),
        ]

    def __str__(self):
        return f"{self.ticket_id} - {self.section_type} - {self.member_name}"

class AssignUsersCategory(models.Model):
    SECTION_TYPES = (
        ("NGO", "NGO"),
        ("OFFICE_BEARER", "OFFICE_BEARER"),
    )

    ticket = models.ForeignKey(
        "Ticket",
        on_delete=models.CASCADE,
        related_name="assigned_user_categories"
    )

    section_type = models.CharField(
            max_length=30,
            choices=(("NGO","NGO"),("OFFICE_BEARER","OFFICE_BEARER")),
            default="NGO",
            db_index=True
        )

    # ✅ for OFFICE_BEARER assignments only
    member_row = models.ForeignKey(
        "TicketMemberRow",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assignments"
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    category = models.ForeignKey(
        "Category",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # ✅ recommended: store selected questions ids
    questions = models.ManyToManyField(
        "Question",
        blank=True,
        related_name="assign_user_categories"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "assign_users_category"
        constraints = [
            models.UniqueConstraint(
                fields=["ticket", "section_type", "member_row", "user", "category"],
                name="uniq_ticket_section_member_user_category"
            )
        ]

    def __str__(self):
        return f"{self.ticket_id} - {self.section_type} - {self.user_id} - {self.category_id}"




class TicketAdverseHistory(models.Model):
    ticket = models.ForeignKey(
        "Ticket",
        related_name="adverse_history",
        on_delete=models.CASCADE
    )

    status_history = models.ForeignKey(
        "TicketStatusHistory",
        related_name="adverse_rows",
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    is_adverse = models.BooleanField(default=False)

    # ✅ FK instead of text
    adverse_reason = models.ForeignKey(
        "AdverseReason",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ticket_adverse_history"
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ticket_adverse_created"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ticket_adverse_history"
        indexes = [
            models.Index(fields=["ticket"]),
            models.Index(fields=["created_at"]),
        ]
        ordering = ["created_at"]

    def __str__(self):
        return f"Ticket {self.ticket_id} adverse={self.is_adverse} reason={self.adverse_reason}"


class AdverseReason(models.Model):
    name = models.CharField(max_length=200, unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name    
    


class TicketActionTrace(models.Model):
    ticket = models.ForeignKey("Ticket", on_delete=models.CASCADE, related_name="action_traces")
    # store your button/action name (free text)
    action_key = models.CharField(max_length=100, db_index=True)   # ex: "PRINT", "MAIL", "MANUAL_SEND"
    # tracking result
    is_success = models.BooleanField(default=False)
    status_text = models.CharField(max_length=255, blank=True, null=True)  # ex: "PDF generated", "SMTP failed"
    error_text = models.TextField(blank=True, null=True)
    # who did it + when
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    performed_at = models.DateTimeField(auto_now_add=True)
    office_file_no = models.CharField(max_length=150, blank=True, null=True)
    # optional extra data (mail ref, file path, etc.)
    meta = models.JSONField(null=True, blank=True)
    class Meta:
        db_table = "ticket_action_trace"
        indexes = [
            models.Index(fields=["ticket", "is_success", "action_key"]),
        ]
        ordering = ["-performed_at"]
    def __str__(self):
        return f"{self.ticket_id} {self.action_key} success={self.is_success}"



class TicketNotification(models.Model):
    """In-app notification for ticket events (assignments, etc.)."""

    class NotificationType(models.TextChoices):
        TICKET_ASSIGNED = "ticket_assigned", "Ticket assigned"
        TICKET_CREATED = "ticket_created", "Ticket created"
        TICKET_REASSIGNED = "ticket_reassigned", "Ticket reassigned"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ticket_notifications",
    )
    ticket = models.ForeignKey(
        "Ticket",
        on_delete=models.CASCADE,
        related_name="notifications",
    )
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

    def __str__(self):
        return f"{self.recipient_id} · {self.notification_type} · ticket #{self.ticket_id}"


class Signater(models.Model):
    STATUS_CHOICES = (
        ("active", "Active"),
        ("inactive", "Inactive"),
    )

    ranks = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")

    class Meta:
        db_table = "signater"

    def __str__(self):
        return self.ranks


class TicketSignater(models.Model):
    ticket = models.ForeignKey(
        "Ticket",
        on_delete=models.CASCADE,
        related_name="ticket_signaters"
    )
    signater = models.ForeignKey(
        "Signater",
        on_delete=models.CASCADE,
        related_name="ticket_signaters"
    )
    action_type = models.CharField(max_length=255, blank=True, null=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ticket_signaters"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ticket_signater"
        constraints = [
            models.UniqueConstraint(
                fields=["ticket", "user", "action_type"],
                name="unique_ticket_user_signater_action_type"
            )
        ]

    def __str__(self):
        return f"Ticket {self.ticket_id} - User {self.user_id} - {self.action_type} - Signater {self.signater_id}"
    


class NgoUoDocument(models.Model):
    rcn = models.CharField(max_length=50, null=True, blank=True)
    association_name = models.CharField(max_length=255, null=True, blank=True)

    document_category = models.CharField(max_length=10)  # uo/report
    doc_type = models.CharField(max_length=20)           # pdf/excel/csv/image/other

    original_name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)         # DB column is file_path

    mime_type = models.CharField(max_length=150, null=True, blank=True)
    file_ext = models.CharField(max_length=20, null=True, blank=True)
    file_size = models.BigIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "ngo_uo_documents"
        managed = False