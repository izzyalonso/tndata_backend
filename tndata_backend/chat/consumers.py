"""
These consumers handle our chat communications over a websocket.

"""
import hashlib
import json

from channels import Channel, Group
from channels.sessions import enforce_ordering
from channels.auth import channel_session_user, channel_session_user_from_http

from django.contrib.auth import get_user_model
from django.utils import timezone

from redis_metrics import metric

from .models import ChatMessage
from .utils import (
    decode_message_text,
    generate_room_name,
    get_user_details,
    get_user_from_message,
    log_messages_to_redis,
)


def chat_message_consumer(message):
    """Given a message, this creates a DB object and sends the message to a
    group. The given message should have the following content:

    - user_id: ID of the user who created the message.
    - room: name of the room the message was sent to.
    - text: text of the message.

    """
    try:
        User = get_user_model()
        user = User.objects.get(pk=message.content['user_id'])
        room = message.content['room']
        text = message.content['text']
        digest = message.content.get('digest', '')
        ChatMessage.objects.create(user=user, room=room, text=text, digest=digest)
    except (User.DoesNotExist, KeyError):
        pass


def mark_as_read_consumer(message):
    """Given a message, query the DB for the matching ChatMessage and mark
    it as read. The given message should have the following content:

    - digest: text of the message.

    """
    try:
        digest = message.content.get('digest', '')
        ChatMessage.objects.filter(digest=digest).update(read=True)
    except KeyError:
        pass


@enforce_ordering(slight=True)
@channel_session_user  # Gives us a channel_session + user
def ws_message(message):
    """Handle messages received by the websocket. This consumer figures out
    what to do with chat messages that are sent by clients (either JS or mobile)

    For reference, the following are important `message` attributes and info.

    - message.channel - the channel object.
    - message.channel_layer -
    - message.channel_session - Sessions, but for channels.
    - message.content - dict of the stuff we're usually interested in:

        {
            'order': 1,
            'path': '/chat/995/',
            'reply_channel': 'websocket.send!fMCqdsWviiwR',
            'text': JSON-encoded string.
        }

    """
    log_messages_to_redis(message.content)

    room = message.channel_session.get('room')
    if room:
        # Look up the user that sent the message
        user = get_user_from_message(message)
        name, avatar = get_user_details(user)

        # ---------------------------------------------------------------------
        # The following is the current format for our recieved message data.
        # This needs to work for both the web app & mobile.
        #
        #  {
        #    text: text of the message,
        #    from: (optional) user ID of person sending it.
        #    token: OPTIONAL token
        #  }
        #
        # However, read recipts will arrive in a format like this:
        #
        #   {
        #       received: digest
        #   }
        # ---------------------------------------------------------------------
        message_text, message_type = decode_message_text(message)

        if message_type == 'message':
            # Construct message sent back to the client.
            user_id = user.id if user else ''
            now = timezone.now().strftime("%c")
            digest = '{}/{}/{}'.format(message_text, user_id, now)
            digest = hashlib.md5(digest.encode('utf-8')).hexdigest()
            payload = {
                'from_id': user.id if user else '',
                'from': name,
                'message': "{}".format(message_text),
                'avatar': avatar,
                'digest': digest,
            }

            # Send to users for display
            Group(room).send({'text': json.dumps(payload)})

            # Now, send it to the channel to create the ChatMessage object.
            Channel("create-chat-message").send({
                "room": room,
                "text": message_text,
                "user_id": user.id,
                "digest": digest,
            })
        elif message_type == 'receipt':
            Channel("mark-chat-message-as-read").send({
                "digest": message_text,
            })
        metric('websocket-message', category="Chat")


@enforce_ordering(slight=True)
@channel_session_user_from_http  # Give us session + user from http session.
def ws_connect(message):
    """Handles when clients connect to a websocket.
    Connected to the `websocket.connect` channel."""
    log_messages_to_redis(message.content)

    # Get the connected user.
    user = get_user_from_message(message)
    if user:
        # ---------------------------------------------------------------------
        # TODO: URL for groups looks like: /chat/group/1-test-group/
        # we need to construct a room name for that? And alter the below.
        #
        # TODO: OR EVEN BETTER... specify a room in the header or as part
        # of a message payload, rather than in a url. This allows the mobile
        # client to use a single websocket connection, rather than a different
        # connection for each room.
        #
        # 1. specify room when connectiong.
        # 2. specify room as part of message payload?
        # 3. ... ?
        # ---------------------------------------------------------------------

        # 1-1 chat rooms between a logged-in user and a path-defined user.
        # path will be something like `/chat/username/`
        try:
            path = message.content['path'].strip('/').split('/')[1]
        except IndexError:
            path = 'unknown'

        room = generate_room_name((path, user))

        # Save the room name and the user's ID in channel session sessions.
        message.channel_session['room'] = room
        message.channel_session['user_id'] = user.id

        Group(room).add(message.reply_channel)

        payload = {
            'from_id': '',
            'from': 'system',
            'message': "{} joined.".format(user.get_full_name() or user),
        }
        Group(room).send({'text': json.dumps(payload)})
        metric('websocket-connect', category="Chat")


@enforce_ordering(slight=True)
@channel_session_user  # Gives us a session store + a user
def ws_disconnect(message):
    """Handles when clients disconnect from a websocket.
    Connected to the `websocket.disconnect` channel."""
    log_messages_to_redis(message.content)

    user = get_user_from_message(message)

    # Pull the room from the channel's session.
    room = message.channel_session.get('room')
    if room:
        payload = {
            'from_id': '',
            'from': 'system',
            'message': "{} left.".format(user.get_full_name() or user),
        }
        Group(room).send({'text': json.dumps(payload)})
        Group(room).discard(message.reply_channel)
        metric('websocket-disconnect', category="Chat")
