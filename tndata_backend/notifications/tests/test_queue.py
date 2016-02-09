from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from .. models import GCMDevice, GCMMessage
from .. queue import UserQueue


def datetime_utc(*args):
    """Make a UTC dateime object."""
    return timezone.make_aware(datetime(*args), timezone.utc)


class TestUserQueue(TestCase):
    """Tests for the `GCMDevice` model."""

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_user('uq', 'uq@example.com', 'pass')
        cls.device = GCMDevice.objects.create(
            user=cls.user,
            registration_id="REGISTRATIONID",
            device_id="DEVICEID"
        )
        cls.deliver_date = timezone.now() + timedelta(days=1)

    def test__key(self):
        msg = GCMMessage.objects.create(self.user, "A", "A", self.deliver_date)
        expected = "uq:1:{}:test".format(self.deliver_date.strftime("%Y-%m-%d"))
        actual = UserQueue(self.msg)._key("test")
        self.assertEqual(expected, actual)
        msg.delete()  # clean up

    def test_count(self):
        msg = GCMMessage.objects.create(self.user, "X", "X", self.deliver_date)
        uq = UserQueue(msg)
        self.assertEqual(uq.count(), 0)

        # now add the message to the queue
        uq.add()
        self.assertEqual(uq.count(), 1)

        msg.delete()  # clean up
        self.assertEqual(uq.count(), 0)

    def test_full(self):
        # When the queue is empty
        self.assertFalse(UserQueue(self.msg).full())

        # When we're over the limit (temporarily set to 1)
        msg = GCMMessage.objects.create(self.user, "A", "A", self.deliver_date)
        uq = UserQueue(msg, limit=1)
        uq.add()
        self.assertTrue(uq.full())

        msg.delete()  # clean up

    def test_add(self):
        # when the queue is not full.
        a = GCMMessage.objects.create(self.user, "A", "A", self.deliver_date)
        job = UserQueue(a).add()
        self.assertIsNotNone(job)

        # when the queue is full.
        b = GCMMessage.objects.create(self.user, "B", "B", self.deliver_date)
        job = UserQueue(b, limit=1).add()
        self.assertIsNone(job)

        # clean up
        a.delete()
        b.delete()

    def test_list(self):
        msg = GCMMessage.objects.create(self.user, "X", "X", self.deliver_date)
        uq = UserQueue(msg)
        job = uq.add()
        self.assertIn(job, uq.list())

        msg.delete()  # clean up

    def test_remove(self):
        msg = GCMMessage.objects.create(self.user, "X", "X", self.deliver_date)
        UserQueue(msg).remove()  # TODO: this doesn't do anything
        msg.delete()  # clean up
