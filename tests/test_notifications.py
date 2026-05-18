from django.contrib.auth import get_user_model
from django.test import TestCase

from tickets.models import Ticket, TicketNotification, TicketReassignment
from tickets.notification_service import notify_ticket_assignees, notify_ticket_reassignees

User = get_user_model()


class TicketNotificationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.creator = User.objects.create_user(
            username="creator",
            email="creator@example.com",
            password="test-pass-123",
        )
        cls.assignee = User.objects.create_user(
            username="assignee",
            email="assignee@example.com",
            password="test-pass-123",
        )
        cls.other = User.objects.create_user(
            username="other",
            email="other@example.com",
            password="test-pass-123",
        )

    def _make_ticket(self):
        return Ticket.objects.create(
            title="Test ticket",
            created_by=self.creator,
            status="open",
        )

    def test_create_assign_notifies_assignee_not_creator(self):
        ticket = self._make_ticket()
        notify_ticket_assignees(
            ticket=ticket,
            assignee_ids={self.assignee.id, self.creator.id},
            actor=self.creator,
        )
        self.assertEqual(
            TicketNotification.objects.filter(
                recipient=self.assignee,
                notification_type=TicketNotification.NotificationType.TICKET_ASSIGNED,
            ).count(),
            1,
        )
        self.assertFalse(TicketNotification.objects.filter(recipient=self.creator).exists())

    def test_m2m_signal_on_create(self):
        ticket = self._make_ticket()
        before = TicketNotification.objects.count()
        ticket.assigned_users.add(self.assignee)
        self.assertEqual(TicketNotification.objects.count(), before + 1)

    def test_m2m_signal_on_reassign(self):
        ticket = self._make_ticket()
        ra = TicketReassignment.objects.create(
            ticket=ticket,
            reassigned_by=self.creator,
            reason="test",
        )
        before = TicketNotification.objects.count()
        ra.new_assigned_users.add(self.assignee)
        self.assertEqual(TicketNotification.objects.count(), before + 1)
