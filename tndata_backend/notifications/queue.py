import logging
import sys
import traceback

from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from redis_metrics import metric
import django_rq
import waffle

from utils.slack import post_private_message


logger = logging.getLogger(__name__)


def _log_slack(msg, username):
    SLACK_USERS = {
        # Local account: slack username
        'bkmontgomery': 'bkmontgomery',
        # 'ringram': 'ringram',
    }
    if SLACK_USERS.get(username) and settings.DEBUG and not settings.STAGING:
        post_private_message(SLACK_USERS[username], msg)


def get_scheduler(queue='default'):
    return django_rq.get_scheduler('default')


# NOTE: This Module-level scheduler is our interface to putting messages
#       on the notifications task queue.
scheduler = get_scheduler()


def send(message_id):
    """Given an ID for a GCMMessage object, send the message via GCM."""
    try:
        from . models import GCMMessage
        msg = GCMMessage.objects.get(pk=message_id)
        msg.send()  # NOTE: sets a metric on successful sends.
    except Exception as e:
        # NOTE: If for some reason, a message got queued up, but something
        # happend to the original GCMMessage, and it's pre-delete signal handler
        # failed, we'd get this exception. OR if something happend during
        # delivery to GCM, we'd get here.
        exc_type, exc_value, exc_traceback = sys.exc_info()

        args = (message_id, "queue.send()", e, settings.SITE_URL)
        log = "[{}] FAILED: {}: {} ({})".format(*args)
        logger.error(log.replace("\n", ""))

        # Include the traceback in the slack message.
        tb = traceback.format_exception(exc_type, exc_value, exc_traceback)
        log = "{}\n```{}```".format(log, "\n".join(tb))
        _log_slack(log, 'bkmontgomery')


def enqueue(message):
    """Given a GCMMessage object, add it to the queue of messages to be sent.

    - message: An instance of a GCMMessage

    Returns an rq Job instance (see job.id) or None if the message could not
    be scheduled.

    NOTE: This function records one of the following metrics:

    - GCM Message Scheduled (when a message is scheduled successfully)
    - Message Scheduling Failed (when it is not)

    Additionally, if the `notifications-user-userqueue` switch is enabled,
    the message will get queued throught the UserQueue, otherwise it
    gets enqueued in the scheduler directly.

    """
    job = None

    # Only queue up messages for the future or messages that should
    # have been sent within the past hour
    now = timezone.now() - timedelta(hours=1)
    is_upcoming = now < message.deliver_on

    if message.user and is_upcoming:
        if waffle.switch_is_active('notifications-user-userqueue'):
            # Enqueue messages through the UserQueue.
            job = UserQueue(message).add()
        else:
            job = scheduler.enqueue_at(message.deliver_on, send, message.id)
    if job:
        # Record a metric so we can see queued vs sent?
        metric('GCM Message Scheduled', category='Notifications')
    else:
        # Record a metric so we can see queued vs sent?
        metric('Message Scheduling Failed', category='Notifications')

    return job


def messages():
    """Return a list of jobs that are scheduled with their scheduled times.

    Returned data is a list of (Job, datetime) tuples.

    """
    return scheduler.get_jobs(with_times=True)


def clear():
    """Clear ALL scheduled jobs in the queue."""
    for job in scheduler.get_jobs():
        scheduler.cancel(job)


def cancel(job_id):
    """Cancel a scheduled job, given its ID."""
    scheduler.cancel(job_id)


class TotalCounter:
    """Descriptor to count total number of queued messages for the UserQueue.
    This class persists its value in redis, but gives us a nicer interface
    for changing the value."""

    def __init__(self):
        self.conn = django_rq.get_connection('default')

    def __get__(self, instance, owner):
        # Use the instance's key to retrieve the value.
        count = int(self.conn.get(instance._key("count")) or 0)
        return count if count > 0 else 0  # Never drop lower than zero

    def __set__(self, instance, value):
        if value <= 0:
            value = 0
        key = instance._key("count")
        self.conn.set(key, value)
        self.conn.expire(key, timedelta(days=2))
        return value


class UserQueue:
    """This class implements a single user's view of their own queue of
    notifications (GCMMessages) for a given day. It stores details in redis,
    and knows how to schedule a message for delivery using rq-scheduler.

    ## Priorities.

    A GCMMessage has a priority, and the UserQueue (this class) will respect
    that, queueing up messages for delivery at the correct priority, while
    respeciting the overall limit (total number of messages to be sent for
    the day). For example, we currently support the following queues:

    - low: typically these messages are the least important, and will be the
      first messages bumped from delivery once the limit is met.
    - medium: ...
    - high: ... High-priority queues are reserved for the **most important**
      messages that must be delivered. This queue ignores the daily limit, so
      it's possible to go over the limit (use as a last resort).

    ## Methods

    - count: Total number of messages queued up for delivery for the day.
    - full : Boolean: are we at (or over) the daily limit
    - add: Add a message to the queue and schedule it for delivery, returning
      a Job or None (if adding failed)
    - list: Return a list of job IDs
    - remove: Remove the message from the queue.

    ## Examples: TODO

    """
    count = TotalCounter()  # Total Counter for all daily messages

    def __init__(self, message, queue='default', send_func=send):
        self.conn = django_rq.get_connection('default')
        self.send_func = send_func
        self.message = message
        self.limit = message.get_daily_message_limit()
        self.priority = getattr(message, 'priority', message.LOW)
        self.user = message.user
        self.date_string = message.deliver_on.date().strftime("%Y-%m-%d")

        # Since we only queue up messages 24 hours in advance, we can
        # auto-expire any values after a couple days. This can be a timedelta
        # object;
        self.expire = timedelta(days=2)

    def _key(self, name):
        """Construct a redis key for the given name. Keys are of the form:

            uq:{user_id}:{date_string}:{name}

        For example:

            uq:1:2016-02-10:count   -- Total daily message count.
            uq:1:2016-02-10:low     -- Key for the low-priority queue.
            uq:1:2016-02-10:high    -- Key for the high-priority queue.

        Returns a string.

        """
        return "uq:{user_id}:{date_string}:{name}".format(
            user_id=self.user.id,
            date_string=self.date_string,
            name=name
        )

    @staticmethod
    def clear(user, date=None):
        """Clear all of the redis queue data associated with the given user
        for the given date (or today)."""
        if date is None:
            date = timezone.now()
        date_string = date.strftime("%Y-%m-%d")
        conn = django_rq.get_connection('default')

        # Redis keys for the count, and all queues.
        keys = [
            'uq:{user_id}:{date_string}:count',
            'uq:{user_id}:{date_string}:low',
            'uq:{user_id}:{date_string}:medium',
            'uq:{user_id}:{date_string}:high',
        ]
        keys = [k.format(user_id=user.id, date_string=date_string) for k in keys]
        conn.delete(*keys)

    @staticmethod
    def get_data(user, date=None):
        """Return a dict of data (redis keys/values) for the UserQueue for the
        given date."""
        if date is None:
            date = timezone.now()
        date_string = date.strftime("%Y-%m-%d")
        conn = django_rq.get_connection('default')

        # Redis keys for the count, and all queues.
        keys = [
            'uq:{user_id}:{date_string}:count',
            'uq:{user_id}:{date_string}:low',
            'uq:{user_id}:{date_string}:medium',
            'uq:{user_id}:{date_string}:high',
        ]
        keys = [k.format(user_id=user.id, date_string=date_string) for k in keys]

        # Get the list values, and convert them from bytes to utf
        data = {k: conn.lrange(k, 0, 100) for i, k in enumerate(keys) if i > 0}
        for key, values in data.items():
            data[key] = [v.decode('utf8') for v in values]
        try:
            data[keys[0]] = int(conn.get(keys[0]))  # then include the count
        except TypeError:
            # If `count` is None
            data[keys[0]] = 0
        return data

    @property
    def num_low(self):
        return self.conn.llen(self._key("low"))

    @property
    def num_medium(self):
        return self.conn.llen(self._key("medium"))

    @property
    def num_high(self):
        return self.conn.llen(self._key("high"))

    def full(self):
        """Is the user's daily queue full? Returns True or False"""
        return self.count >= self.limit

    def _enqueue(self):
        """Put the message in the appropriate queue and schedule for delivery,
        taking care to update the total count.

        If the message is enqueued successfully, the Job instances is returned.

        """
        # Enqueue the job...
        job = scheduler.enqueue_at(
            self.message.deliver_on,
            self.send_func,
            self.message.id
        )

        # Keep up with a list of job ids for the day.
        # We need to keep a separate list for each priority, so we
        # can figure out whenter to drop some and add others once the
        # limit is met.
        key = self._key(self.priority)
        self.conn.rpush(key, job.id)
        self.conn.expire(key, self.expire)

        # And count the total number of items queued up for the day.
        self.count += 1
        return job

    def add(self):
        """Adds the message to the queue *if* there's room.

        Returns the scheduled Job object (or None if the job was not added).

        """
        # Scenarios:
        #
        # Queue is not full. Schedule it.
        # Queue is full, msg is high priority. Schedule it.
        # Queue is full, msg is medium priority, try to bump a low priority msg,
        #   then schedule.
        # Queue is full, msg is low priority, ignore.

        job = None
        if not self.full() or self.priority == 'high':
            job = self._enqueue()
        elif self.priority == 'medium' and self.num_low > 0:
            # Bump a lower-priority message
            self.bump_from_queue('low')
            job = self._enqueue()
        return job

    def list(self):
        """Return a list of today's Jobs (Job instances) scheduled at the same
        priority as the current Message."""
        k = self._key(self.priority)
        num_items = self.conn.llen(k)

        # Get all the job ids stored at the given priority.
        job_ids = self.conn.lrange(k, 0, num_items)

        # Redis returns data in bytes, so we need to decode to utf-8
        job_ids = [job_id.decode('utf8') for job_id in job_ids]
        return [job for job in scheduler.get_jobs() if job.id in job_ids]

    def bump_from_queue(self, priority='low'):
        """Bump a message from a queue (ie. remove an already-queued message in
        favor of a higher-priority one.

        This removes the items from the end of the given priority queue, and
        cancels it's scheduled delivery.

        """
        # Remove the item from the priority queue
        job_id = self.conn.rpop(self._key(priority))
        job_id = job_id.decode('utf8')

        # Decrement the total count.
        self.count -= 1

        # And cancel the job (it's ok if this already happened)
        cancel(job_id)

    def remove(self):
        """Remove the message (eg: when deleteing GCMMessage)"""
        k = self._key(self.priority)

        # Pull all the job ids off the queue (we'll re-add them later), keeping
        # the ones we're not removing
        job_ids = [
            job.id for job in self.list()
            if job.id != self.message.queue_id
        ]

        # Then delete the queue, and re-add the keepers.
        self.conn.delete(k)
        if len(job_ids) > 0:
            self.conn.rpush(k, *job_ids)

        # Decrement the total count.
        self.count -= 1

        # And cancel the job (it's ok if this already happened)
        cancel(self.message.queue_id)
