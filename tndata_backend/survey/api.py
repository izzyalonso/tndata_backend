import random
from django.db.models import ObjectDoesNotExist
from rest_framework import exceptions, mixins, viewsets
from rest_framework.authentication import (
    SessionAuthentication,
    TokenAuthentication,
)
from rest_framework.response import Response

from . import models
from . import permissions
from . import serializers


class InstrumentViewSet(viewsets.ReadOnlyModelViewSet):
    """This is a read-only endpoint for all available Instruments.

    Instruments contain the following attributes:

    * id: The database ID for the Instrument
    * title: The title of the instrument
    * description: A description of the instrument.
    * instructions: Instructions that apply to all questions in the instrument

    ----

    """
    queryset = models.Instrument.objects.all()
    serializer_class = serializers.InstrumentSerializer

    def list(self, request, *args, **kwargs):
        resp = super(InstrumentViewSet, self).list(request, *args, **kwargs)
        # Hack the data to include FQDNs for the response_url item.
        for item in resp.data['results']:
            for q in item['questions']:
                q['response_url'] = self.request.build_absolute_uri(q['response_url'])
        return resp

    def retrieve(self, request, *args, **kwargs):
        resp = super(InstrumentViewSet, self).retrieve(request, *args, **kwargs)
        for q in resp.data['questions']:
            q['response_url'] = self.request.build_absolute_uri(q['response_url'])
        return resp


class RandomQuestionViewSet(mixins.ListModelMixin,
                            mixins.RetrieveModelMixin,
                            viewsets.GenericViewSet):
    """This endpoint retuns a single, random Question. The returned data
    may represent one of three different types of questions: Binary (Yes/No),
    Likert, Multiple Choice, or Open-Ended.

    The questions provided by this endpoint are guaranteed to not have been
    answered by the authenticated user.

    ## Question Types

    For details on the different question types, see their respective api docs:

    * [BinaryQuestion](/api/survey/binary/)
    * [LikertQuestion](/api/survey/likert/)
    * [MultipleChoiceQuestion](/api/survey/multiplechoice/)
    * [OpenEndedQuestion](/api/survey/open/)

    ## Additional information

    This endpoint includes two pieces of additional information in its response:

    * `question_type` -- tells you the type of question returned, and will be
      on of `likertquestion`, `multiplechoicequestion`, or `openendedquestion`
    * `response_url` -- is the link to the endpoint to which response data
      should be POSTed.

    ## Filtering

    These questions can be filtered by Instrument (see the
    [survey/instruments endpoint](/api/survey/instruments/)) using a
    querystring paramter. Provide an instrument ID and this endpoint will return
    questions within that instrument: `/api/survey/?instrument={instrument_id}`

    ## OK, not so random, after all

    If you provide a concatenation of a question's `question_type` and its
    `id`, you will get a representation of that question. For example, given a
    `LikertQuestion` whose ID is 1, you could retrive it with an identifier of
    `likertquestion-1`:
    [/api/survey/likertquestion-1/](/api/survey/likertquestion-1)

    ----

    """
    # individual questions can be returned via an concatenation of the question
    # type and the question id, e.g. "openendedquestion-1"
    lookup_field = "type_and_id"
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = [permissions.IsOwner]

    # Since this viewset serves up data from multiple types of models, this
    # dictionary contains some detail that help us work with the different
    # models; The key for each item is the model's lower case __name__
    question_models = {
        models.BinaryQuestion.__name__.lower(): {
            'model': models.BinaryQuestion,
            'serializer': serializers.BinaryQuestionSerializer,
            'related_response_name': 'binaryresponse',
        },
        models.LikertQuestion.__name__.lower(): {
            'model': models.LikertQuestion,
            'serializer': serializers.LikertQuestionSerializer,
            'related_response_name': 'likertresponse',
        },
        models.MultipleChoiceQuestion.__name__.lower(): {
            'model': models.MultipleChoiceQuestion,
            'serializer': serializers.MultipleChoiceQuestionSerializer,
            'related_response_name': 'multiplechoiceresponse',
        },
        models.OpenEndedQuestion.__name__.lower(): {
            'model': models.OpenEndedQuestion,
            'serializer': serializers.OpenEndedQuestionSerializer,
            'related_response_name': 'openendedresponse',
        }
    }

    def _get_random_question(self, user, instrument=None):
        questions = []
        # Find all the available questions that the user has not answered.
        for q in self.question_models.values():
            kwargs = {"{0}__user".format(q['related_response_name']): user}
            qs = q['model'].objects.available().exclude(**kwargs)
            if instrument:
                qs = qs.filter(instruments=instrument)
            questions.extend(list(qs))

        # TODO: Respect the questions' Priority field.

        # Pick a random one.
        if len(questions) > 0:
            item = random.choice(questions)
            api_path = item.get_api_response_url()  # Grab the URI for the response.
            model_name = item.__class__.__name__.lower()  # remember which model

            # Serialize it.
            item = self.question_models[model_name]['serializer']().to_representation(item)
            item['response_url'] = self.request.build_absolute_uri(api_path)
            return item
        return {}

    def list(self, request):
        if not request.user.is_authenticated():
            raise exceptions.NotAuthenticated
        instrument = request.GET.get("instrument", None)
        item = self._get_random_question(request.user, instrument)
        return Response(item)

    def retrieve(self, request, *args, **kwargs):
        """Retrieve a single question, given: "question_type-id", e.g.:

            /api/survey/openendedquestion-1/

        """
        if not request.user.is_authenticated():
            raise exceptions.NotAuthenticated

        try:
            qt, pk = kwargs.get(self.lookup_field, '-').split("-")
            item = self.question_models[qt]['model'].objects.get(pk=pk)
            item = self.question_models[qt]['serializer']().to_representation(item)
            item['response_url'] = self.request.build_absolute_uri(item['response_url'])
            return Response(item)
        except ObjectDoesNotExist:
            raise exceptions.NotFound


class LikertQuestionViewSet(viewsets.ReadOnlyModelViewSet):
    """This is a read-only endpoint for all available Likert Questions.

    Likert Questions contain the following attributes:

    * id: The database ID for the Question.
    * text: The text of the question. This is what the user should see.
    * order: The order in which multiple questions should be displayed.
    * available: Boolean. Whether or not this question should be available to
        users. This should always be `true` for this endpoint.
    * options: The options available to a user for answering this question.
      For likert questions, this is a list of objects with `id` and `text`
      attributes.
    * instructions: The instructions for the user answering the question (if any)
    * updated: Date & time the question was last updated.
    * created: Date & time the question was created.

    To save a User's response, POST the question ID and the option ID to the
    [LikertResponse](/api/survey/likert/responses/) endpoint:

        {question: ID, 'selected_option': OPTION_ID}

    ----

    """
    queryset = models.LikertQuestion.objects.available()
    serializer_class = serializers.LikertQuestionSerializer


class BinaryQuestionViewSet(viewsets.ReadOnlyModelViewSet):
    """This is a read-only endpoint for all available Binary Questions.

    Binary Questions contain the following attributes:

    * id: The database ID for the Question.
    * order: The order in which questions should be displayed (if displaying
      multiple items)
    * text: The text of the question. This is what the user should see.
    * available: Boolean. Whether or not this question should be available to
        users. This should always be `true` for this endpoint.
    * options: The options available to a user for answering this question.
      For binary questions, this is a list of objects with `id` and `text`
      attributes.
    * instructions: The instructions for the user answering the question (if any)
    * updated: Date & time the question was last updated.
    * created: Date & time the question was created.

    To save a User's response, POST the question ID and the option ID to the
    [BinaryResponse](/api/survey/binary/responses/) endpoint:

        {question: ID, 'selected_option': OPTION_ID}

    ----

    """
    queryset = models.BinaryQuestion.objects.available()
    serializer_class = serializers.BinaryQuestionSerializer


class MultipleChoiceQuestionViewSet(viewsets.ReadOnlyModelViewSet):
    """This is a read-only endpoint for all available Multiple Choice Questions.

    Multiple Choice Questions contain the following attributes:

    * id: The database ID for the Question.
    * text: The text of the question. This is what the user should see.
    * order: The order in which multiple questions should be displayed.
    * available: Boolean. Whether or not this question should be available to
        users. This should always be `true` for this endpoint.
    * options: The options available to a user for answering this question.
      For multiple choice questions, this is a list of objects with `id` and
      `text` attributes.
    * instructions: The instructions for the user answering the question (if any)
    * updated: Date & time the question was last updated.
    * created: Date & time the question was created.

    To save a User's response, POST the question ID and the option ID to the
    [MultipleChoiceResponse](/api/survey/multiplechoice/responses/) endpoint:

        {question: ID, 'selected_option': OPTION_ID}

    ----

    """
    queryset = models.MultipleChoiceQuestion.objects.available()
    serializer_class = serializers.MultipleChoiceQuestionSerializer


class OpenEndedQuestionViewSet(viewsets.ReadOnlyModelViewSet):
    """This is a read-only endpoint for all available Open-Ended Questions.

    Open-Ended Questions contain the following attributes:

    * id: The database ID for the Question.
    * input_type: The type of data to allow as input. Will be one of:
      `text`, `datetime`, or `numeric`.
    * text: The text of the question. This is what the user should see.
    * order: The order in which multiple questions should be displayed.
    * available: Boolean. Whether or not this question should be available to
        users. This should always be `true` for this endpoint.
    * instructions: The instructions for the user answering the question (if any)
    * updated: Date & time the question was last updated.
    * created: Date & time the question was created.

    To save a User's response, POST the question ID and the user's response
    to the [OpenEndedResponse](/api/survey/open/responses/) endpoint:

        {question: ID, 'response': USER_RESPONSE}

    ----

    """
    queryset = models.OpenEndedQuestion.objects.available()
    serializer_class = serializers.OpenEndedQuestionSerializer


class BinaryResponseViewSet(mixins.CreateModelMixin,
                            mixins.ListModelMixin,
                            mixins.RetrieveModelMixin,
                            viewsets.GenericViewSet):
    """This endpoint lists the [BinaryQuestion](/api/survey/binary/)s to which
    a [User](/api/users/) has responded.

    GET requests to this page will list all questions belonging to the User.

    ## Adding a Response

    To save a User's response to a question, POST to this endpoint with the
    following data:

        {'question': QUESTION_ID, 'selected_option': VALUE}

    Where value is one of the given options for the question.

    ## Updating/Deleting a Response.

    Updating or deleting a response is currently not supported.

    ## Viewing the individual response

    Additionally, you can retrieve information for a single Response through
    the endpoint including it's ID: `/api/survey/binary/responses/{response_id}/`.

    ----

    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    queryset = models.BinaryResponse.objects.all()
    serializer_class = serializers.BinaryResponseSerializer
    permission_classes = [permissions.IsOwner]

    def get_queryset(self):
        return self.queryset.filter(user__id=self.request.user.id)

    def create(self, request, *args, **kwargs):
        """Only create objects for the authenticated user."""
        request.data['user'] = request.user.id
        return super(BinaryResponseViewSet, self).create(request, *args, **kwargs)


class LikertResponseViewSet(mixins.CreateModelMixin,
                            mixins.ListModelMixin,
                            mixins.RetrieveModelMixin,
                            viewsets.GenericViewSet):
    """This endpoint lists the [LikertQuestion](/api/survey/likert/)s to which
    a [User](/api/users/) has responded.

    GET requests to this page will list all questions belonging to the User.

    ## Adding a Response

    To save a User's response to a question, POST to this endpoint with the
    following data:

        {'question': QUESTION_ID, 'selected_option': VALUE}

    Where value is one of the given options for the question.

    ## Updating/Deleting a Response.

    Updating or deleting a response is currently not supported.

    ## Viewing the individual response

    Additionally, you can retrieve information for a single Response through
    the endpoint including it's ID: `/api/survey/likert/responses/{response_id}/`.

    ----

    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    queryset = models.LikertResponse.objects.all()
    serializer_class = serializers.LikertResponseSerializer
    permission_classes = [permissions.IsOwner]

    def get_queryset(self):
        return self.queryset.filter(user__id=self.request.user.id)

    def create(self, request, *args, **kwargs):
        """Only create objects for the authenticated user."""
        request.data['user'] = request.user.id
        return super(LikertResponseViewSet, self).create(request, *args, **kwargs)


class OpenEndedResponseViewSet(mixins.CreateModelMixin,
                               mixins.ListModelMixin,
                               mixins.RetrieveModelMixin,
                               viewsets.GenericViewSet):
    """This endpoint lists the [OpenEndedQuestion](/api/survey/open/)s to
    which a [User](/api/users/) has responded.

    GET requests to this page will list all questions belonging to the User.

    ## Adding a Response

    To save a User's response to a question, POST to this endpoint with the
    following data:

        {'question': QUESTION_ID, 'response': "SOME TEXT"}

    ## Updating/Deleting a Response.

    Updating or deleting a response is currently not supported.

    ## Viewing the individual response

    Additionally, you can retrieve information for a single Response through
    the endpoint including it's ID: `/api/survey/openended/responses/{response_id}/`.

    ----

    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    queryset = models.OpenEndedResponse.objects.all()
    serializer_class = serializers.OpenEndedResponseSerializer
    permission_classes = [permissions.IsOwner]

    def get_queryset(self):
        return self.queryset.filter(user__id=self.request.user.id)

    def create(self, request, *args, **kwargs):
        """Only create objects for the authenticated user."""
        request.data['user'] = request.user.id
        return super(OpenEndedResponseViewSet, self).create(request, *args, **kwargs)


class MultipleChoiceResponseViewSet(mixins.CreateModelMixin,
                                    mixins.ListModelMixin,
                                    mixins.RetrieveModelMixin,
                                    viewsets.GenericViewSet):
    """This endpoint lists the [MultipleChoiceQuestion](/api/survey/likert/)s
    to which a [User](/api/users/) has responded.

    GET requests to this page will list all questions belonging to the User.

    ## Adding a Response

    To save a User's response to a question, POST to this endpoint with the
    following data:

        {'question': QUESTION_ID, 'selected_option': OPTION_ID}


    ## Updating/Deleting a Response.

    Updating or deleting a response is currently not supported.

    ## Viewing the individual response

    Additionally, you can retrieve information for a single Response through
    the endpoint including it's ID:
    `/api/survey/multiplechoice/responses/{response_id}/`.

    ----

    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    queryset = models.MultipleChoiceResponse.objects.all()
    serializer_class = serializers.MultipleChoiceResponseSerializer
    permission_classes = [permissions.IsOwner]

    def get_queryset(self):
        return self.queryset.filter(user__id=self.request.user.id)

    def create(self, request, *args, **kwargs):
        """Only create objects for the authenticated user."""
        request.data['user'] = request.user.id
        return super(MultipleChoiceResponseViewSet, self).create(request, *args, **kwargs)
