from collections import defaultdict
from datetime import datetime

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render, redirect

from . import queue
from .models import GCMMessage


@user_passes_test(lambda u: u.is_staff, login_url='/')
def dashboard(request):
    """A simple dashboard for enqueued GCM notifications."""

    jobs = queue.messages()  # Get the enqueued messages
    ids = [job.args[0] for job, _ in jobs]

    message_data = defaultdict(dict)
    fields = ['id', 'title', 'user__id', 'user__email', 'message', 'deliver_on']
    messages = GCMMessage.objects.filter(pk__in=ids).values_list(*fields)
    for msg in messages:
        mid, title, user_id, email, message, deliver_on = msg
        message_data[mid] = {
            'id': mid,
            'title': title,
            'user_id': user_id,
            'email': email,
            'message': message,
            'date_string': deliver_on.strftime("%Y-%m-%d"),
        }

    jobs = [
        (job, scheduled_for, message_data[job.args[0]])
        for job, scheduled_for in jobs
    ]
    context = {
        'jobs': jobs,
        'metrics': ['GCM Message Sent', 'GCM Message Scheduled', ]
    }
    return render(request, "notifications/index.html", context)


@user_passes_test(lambda u: u.is_staff, login_url='/')
def userqueue(request, user_id, date):
    """Return UserQueue details; i.e. the sheduled notifications/jobs for the
    user for a given date.
    """
    user = get_object_or_404(get_user_model(), pk=user_id)
    date = datetime.strptime(date, '%Y-%m-%d')
    data = queue.UserQueue.get_data(user, date)

    # massage that data a bit.
    results = {}
    for key, values in data.items():
        if 'count' in key:
            results['count'] = values
        elif 'low' in key:
            results['low'] = values
        elif 'medium' in key:
            results['medium'] = values
        elif 'high' in key:
            results['high'] = values
    results['date'] = date.strftime("%Y-%m-%d")
    results['user'] = user.get_full_name()
    return JsonResponse(results)


@user_passes_test(lambda u: u.is_staff, login_url='/')
def cancel_job(request):
    """Look for an enqueued job with the given ID and cancel it."""
    job_id = request.POST.get('job_id', None)
    if request.method == "POST" and job_id:
        for job, _ in queue.messages():
            if job.id == job_id:
                job.cancel()
                messages.success(request, "That notification has been cancelled")
                break
    return redirect("notifications:dashboard")


@user_passes_test(lambda u: u.is_staff, login_url='/')
def cancel_all_jobs(request):
    """Cancels all queued messages."""
    if request.method == "POST":
        count = 0
        for job, _ in queue.messages():
            job.cancel()
            count += 1
        messages.success(request, "Cancelled {} notifications.".format(count))
    return redirect("notifications:dashboard")
