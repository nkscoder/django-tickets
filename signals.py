from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from .models import Ticket, TicketReassignment
from .notification_service import notify_ticket_assignees, notify_ticket_reassignees


@receiver(m2m_changed, sender=Ticket.assigned_users.through)
def on_ticket_assigned_users_changed(sender, instance, action, pk_set, **kwargs):
    if action != "post_add" or not pk_set:
        return
    notify_ticket_assignees(ticket=instance, assignee_ids=set(pk_set))


@receiver(m2m_changed, sender=TicketReassignment.new_assigned_users.through)
def on_reassignment_users_changed(sender, instance, action, pk_set, **kwargs):
    if action != "post_add" or not pk_set:
        return
    ticket = instance.ticket
    actor = instance.reassigned_by
    notify_ticket_reassignees(
        ticket=ticket,
        assignee_ids=set(pk_set),
        actor=actor,
    )
