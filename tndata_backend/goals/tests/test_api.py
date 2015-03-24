from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .. models import (
    Action,
    Behavior,
    Category,
    Goal,
    Trigger,
    UserGoal,
    UserBehavior,
    UserCategory,
    UserAction,
)


class TestCategoryAPI(APITestCase):

    def setUp(self):
        self.category = Category.objects.create(
            order=1,
            title='Test Category',
            description='Some explanation!',
            notes="Some notes"
        )

    def tearDown(self):
        Category.objects.filter(id=self.category.id).delete()

    def test_get_category_list(self):
        url = reverse('category-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data['count'], 1)
        c = response.data['results'][0]
        self.assertEqual(c['id'], self.category.id)
        self.assertEqual(c['description'], self.category.description)
        self.assertEqual(c['title'], self.category.title)
        self.assertEqual(c['title_slug'], self.category.title_slug)

    def test_post_category_list(self):
        """Ensure this endpoint is read-only."""
        url = reverse('category-list')
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_get_category_detail(self):
        url = reverse('category-detail', args=[self.category.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.category.id)

    def test_post_category_detail(self):
        """Ensure this endpoint is read-only."""
        url = reverse('category-detail', args=[self.category.id])
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class TestGoalAPI(APITestCase):

    def setUp(self):
        self.category = Category.objects.create(
            order=1,
            title='Test Category',
            description='Some explanation!',
            notes="Some notes"
        )
        self.goal = Goal.objects.create(
            title="Test Goal",
            subtitle="A subtitle",
            description="A Description",
            outcome="The outcome"
        )
        self.goal.categories.add(self.category)

    def tearDown(self):
        Category.objects.filter(id=self.category.id).delete()
        Goal.objects.filter(id=self.goal.id).delete()

    def test_goal_list(self):
        url = reverse('goal-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data['count'], 1)
        obj = response.data['results'][0]
        self.assertEqual(obj['id'], self.goal.id)
        self.assertEqual(obj['title'], self.goal.title)
        self.assertEqual(obj['title_slug'], self.goal.title_slug)
        self.assertEqual(obj['subtitle'], self.goal.subtitle)
        self.assertEqual(obj['description'], self.goal.description)

    def test_goal_list_by_category(self):
        """Ensure we can filter by category."""
        # Create another Goal (not in a catgory)
        g = Goal.objects.create(title="ignore me")

        url = reverse('goal-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)  # Our other goal is here

        # Check the filtered result
        url = "{0}?category={1}".format(url, self.category.id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.goal.id)

        # Clean up.
        g.delete()

    def test_post_goal_list(self):
        """Ensure this endpoint is read-only."""
        url = reverse('goal-list')
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_get_goal_detail(self):
        url = reverse('goal-detail', args=[self.goal.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.goal.id)

    def test_post_goal_detail(self):
        """Ensure this endpoint is read-only."""
        url = reverse('goal-detail', args=[self.goal.id])
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class TestTriggerAPI(APITestCase):

    def setUp(self):
        self.trigger = Trigger.objects.create(name="Test Trigger")

    def tearDown(self):
        Trigger.objects.filter(id=self.trigger.id).delete()

    def test_trigger_list(self):
        url = reverse('trigger-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data['count'], 1)
        obj = response.data['results'][0]
        self.assertEqual(obj['id'], self.trigger.id)
        self.assertEqual(obj['name'], self.trigger.name)

    def test_post_trigger_list(self):
        """Ensure this endpoint is read-only."""
        url = reverse('trigger-list')
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_get_trigger_detail(self):
        url = reverse('trigger-detail', args=[self.trigger.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.trigger.id)

    def test_post_trigger_detail(self):
        """Ensure this endpoint is read-only."""
        url = reverse('trigger-detail', args=[self.trigger.id])
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class TestBehaviorAPI(APITestCase):

    def setUp(self):
        self.category = Category.objects.create(
            order=1,
            title='Test Category',
            description='Some explanation!',
            notes="Some notes"
        )
        self.goal = Goal.objects.create(
            title="Test Goal",
            subtitle="A subtitle",
            description="A Description",
            outcome="The outcome"
        )
        self.behavior = Behavior.objects.create(
            title="Test Behavior",
            description="This is a test",
            informal_list="Do this",
        )
        self.behavior.categories.add(self.category)
        self.behavior.goals.add(self.goal)

    def tearDown(self):
        Category.objects.filter(id=self.category.id).delete()
        Goal.objects.filter(id=self.goal.id).delete()
        Behavior.objects.filter(id=self.behavior.id).delete()

    def test_behavior_list(self):
        url = reverse('behavior-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data['count'], 1)
        obj = response.data['results'][0]
        self.assertEqual(obj['id'], self.behavior.id)
        self.assertEqual(obj['title'], self.behavior.title)
        self.assertEqual(obj['title_slug'], self.behavior.title_slug)
        self.assertEqual(obj['description'], self.behavior.description)
        self.assertEqual(len(obj['goals']), 1)  # Should have 1 goal
        self.assertEqual(obj['goals'][0]['title'], self.goal.title)

    def test_behavior_list_by_category_id(self):
        """Ensure we can filter by category.id."""
        # Create another Behavior (with no Category)
        b = Behavior.objects.create(title="ignore me")

        url = reverse('behavior-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

        # Check the filtered result
        url = "{0}?category={1}".format(url, self.category.id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.behavior.id)

        # Clean up.
        b.delete()

    def test_behavior_list_by_category_title_slug(self):
        """Ensure we can filter by category.title_slug."""
        # Create another Behavior (with no Category)
        b = Behavior.objects.create(title="ignore me")

        url = reverse('behavior-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

        # Check the filtered result
        url = "{0}?category={1}".format(url, self.category.title_slug)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.behavior.id)

        # Clean up.
        b.delete()

    def test_behavior_list_by_goal_id(self):
        """Ensure we can filter by goal.id"""
        # Create another Behavior (with no Goal)
        b = Behavior.objects.create(title="ignore me")

        url = reverse('behavior-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

        # Check the filtered result
        url = "{0}?goal={1}".format(url, self.goal.id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.behavior.id)

        # Clean up.
        b.delete()

    def test_behavior_list_by_goal_title_slug(self):
        """Ensure we can filter by goal.title_slug"""
        # Create another Behavior (with no Goal)
        b = Behavior.objects.create(title="ignore me")

        url = reverse('behavior-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

        # Check the filtered result
        url = "{0}?goal={1}".format(url, self.goal.title_slug)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.behavior.id)

        # Clean up.
        b.delete()

    def test_post_behavior_list(self):
        """Ensure this endpoint is read-only."""
        url = reverse('behavior-list')
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_get_behavior_detail(self):
        url = reverse('behavior-detail', args=[self.behavior.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.behavior.id)

    def test_post_behavior_detail(self):
        """Ensure this endpoint is read-only."""
        url = reverse('behavior-detail', args=[self.behavior.id])
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class TestActionAPI(APITestCase):

    def setUp(self):
        self.category = Category.objects.create(
            order=1,
            title='Test Category',
            description='Some explanation!',
            notes="Some notes"
        )
        self.goal = Goal.objects.create(
            title="Test Goal",
            subtitle="A subtitle",
            description="A Description",
            outcome="The outcome"
        )
        self.behavior = Behavior.objects.create(
            title="Test Behavior",
            description="This is a test",
            informal_list="Do this",
        )
        self.behavior.categories.add(self.category)
        self.behavior.goals.add(self.goal)

        self.action = Action.objects.create(
            title="Test Action",
            sequence_order=1,
            behavior=self.behavior,
            description="This is a test",
        )

    def tearDown(self):
        Category.objects.filter(id=self.category.id).delete()
        Goal.objects.filter(id=self.goal.id).delete()
        Behavior.objects.filter(id=self.behavior.id).delete()
        Action.objects.filter(id=self.action.id).delete()

    def test_action_list(self):
        url = reverse('action-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data['count'], 1)
        obj = response.data['results'][0]
        self.assertEqual(obj['id'], self.action.id)
        self.assertEqual(obj['title'], self.action.title)
        self.assertEqual(obj['title_slug'], self.action.title_slug)
        self.assertEqual(obj['description'], self.action.description)
        self.assertEqual(obj['behavior']['id'], self.behavior.id)

    def test_action_list_by_category_id(self):
        """Ensure we can filter by category.id."""
        # Create another Action (with no Category)
        b = Behavior.objects.create(title='ignore me')
        a = Action.objects.create(title="ignore me", behavior=b)

        url = reverse('action-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

        # Check the filtered result
        url = "{0}?category={1}".format(url, self.category.id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.action.id)

        # Clean up.
        a.delete()
        b.delete()

    def test_action_list_by_category_title_slug(self):
        """Ensure we can filter by category.title_slug."""
        # Create another Action (with no Category)
        b = Behavior.objects.create(title='ignore me')
        a = Action.objects.create(title="ignore me", behavior=b)

        url = reverse('action-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

        # Check the filtered result
        url = "{0}?category={1}".format(url, self.category.title_slug)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.action.id)

        # Clean up.
        a.delete()
        b.delete()

    def test_action_list_by_goal_id(self):
        """Ensure we can filter by goal.id"""
        # Create another Action (with no Goal)
        b = Behavior.objects.create(title='ignore me')
        a = Action.objects.create(title="ignore me", behavior=b)

        url = reverse('action-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

        # Check the filtered result
        url = "{0}?goal={1}".format(url, self.goal.id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.action.id)

        # Clean up.
        a.delete()
        b.delete()

    def test_action_list_by_goal_title_slug(self):
        """Ensure we can filter by goal.title_slug"""
        # Create another Action (with no Goal)
        b = Behavior.objects.create(title='ignore me')
        a = Action.objects.create(title="ignore me", behavior=b)

        url = reverse('action-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

        # Check the filtered result
        url = "{0}?goal={1}".format(url, self.goal.title_slug)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.action.id)

        # Clean up.
        a.delete()
        b.delete()

    def test_action_list_by_behavior_id(self):
        """Ensure we can filter by behavior.id"""
        # Create another Action
        b = Behavior.objects.create(title='ignore me')
        a = Action.objects.create(title="ignore me", behavior=b)

        url = reverse('action-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

        # Check the filtered result
        url = "{0}?behavior={1}".format(url, self.behavior.id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.action.id)

        # Clean up.
        a.delete()
        b.delete()

    def test_action_list_by_behavior_title_slug(self):
        """Ensure we can filter by behavior.title_slug"""
        # Create another Action
        b = Behavior.objects.create(title='ignore me')
        a = Action.objects.create(title="ignore me", behavior=b)

        url = reverse('action-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

        # Check the filtered result
        url = "{0}?behavior={1}".format(url, self.behavior.title_slug)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.action.id)

        # Clean up.
        a.delete()
        b.delete()

    def test_post_action_list(self):
        """Ensure this endpoint is read-only."""
        url = reverse('action-list')
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_get_action_detail(self):
        url = reverse('action-detail', args=[self.action.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.action.id)

    def test_post_action_detail(self):
        """Ensure this endpoint is read-only."""
        url = reverse('action-detail', args=[self.action.id])
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class TestUserGoalAPI(APITestCase):

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create(
            username="test",
            email="test@example.com",
        )
        self.goal = Goal.objects.create(
            title="Test Goal",
            subtitle="A subtitle",
            description="A Description",
            outcome="The outcome"
        )

        self.ug = UserGoal.objects.create(
            user=self.user,
            goal=self.goal,
        )

    def tearDown(self):
        User = get_user_model()
        User.objects.filter(id=self.user.id).delete()
        Goal.objects.filter(id=self.goal.id).delete()
        UserGoal.objects.filter(id=self.ug.id).delete()

    def test_usergoal_list(self):
        """Ensure un-authenticated requests don't expose any results."""
        url = reverse('usergoal-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)

    def test_usergoal_list_authenticated(self):
        """Ensure authenticated requests DO expose results."""
        url = reverse('usergoal-list')
        self.client.credentials(
            HTTP_AUTHORIZATION='Token ' + self.user.auth_token.key
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['user'], self.user.id)
        self.assertEqual(
            response.data['results'][0]['goal']['id'],
            self.goal.id
        )
        self.assertEqual(
            response.data['results'][0]['goal']['title'],
            self.goal.title
        )

    def test_post_usergoal_list_unathenticated(self):
        """Unauthenticated requests should not be allowed to post new UserGoals"""
        url = reverse('usergoal-list')
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_usergoal_list_athenticated(self):
        """Authenticated users Should be able to create a UserGoal."""
        newgoal = Goal.objects.create(title="New", subtitle="New")

        url = reverse('usergoal-list')
        self.client.credentials(
            HTTP_AUTHORIZATION='Token ' + self.user.auth_token.key
        )
        response = self.client.post(url, {"goal": newgoal.id})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(UserGoal.objects.filter(user=self.user).count(), 2)

        # Clean up.
        newgoal.delete()

    def test_post_usergoal_list_multiple_authenticated(self):
        """POST should be allowed for authenticated users"""
        goal_a = Goal.objects.create(title="A", subtitle="New Goal A")
        goal_b = Goal.objects.create(title="B", subtitle="New Goal B")

        url = reverse('usergoal-list')
        self.client.credentials(
            HTTP_AUTHORIZATION='Token ' + self.user.auth_token.key
        )
        post_data = [
            {'goal': goal_a.id},
            {'goal': goal_b.id}
        ]
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure our user is associated with the categories.
        self.assertEqual(self.user.usergoal_set.count(), 3)

        # clean up.
        goal_a.delete()
        goal_b.delete()

    def test_get_usergoal_detail_unauthed(self):
        """Ensure unauthenticated users cannot view this endpoint."""
        url = reverse('usergoal-detail', args=[self.ug.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_usergoal_detail(self):
        """Ensure authenticated users can view this endpoint."""
        url = reverse('usergoal-detail', args=[self.ug.id])
        self.client.credentials(
            HTTP_AUTHORIZATION='Token ' + self.user.auth_token.key
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_post_usergoal_detail_not_allowed(self):
        """Ensure POSTing to the detail endpoint is not allowed."""
        url = reverse('usergoal-detail', args=[self.ug.id])
        response = self.client.post(url, {'goal': 1})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # Even if you're authenticated
        self.client.credentials(
            HTTP_AUTHORIZATION='Token ' + self.user.auth_token.key
        )
        response = self.client.post(url, {'goal': 1})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_put_usergoal_detail_not_allowed(self):
        """Ensure PUTing to the detail endpoint is not allowed."""
        url = reverse('usergoal-detail', args=[self.ug.id])
        response = self.client.put(url, {'goal': 1})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # Even if you're authenticated
        self.client.credentials(
            HTTP_AUTHORIZATION='Token ' + self.user.auth_token.key
        )
        response = self.client.put(url, {'goal': 1})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_usergoal_detail_unauthed(self):
        """Ensure unauthenticated users cannot delete."""
        url = reverse('usergoal-detail', args=[self.ug.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_usergoal_detail(self):
        """Ensure authenticated users can deelte."""
        url = reverse('usergoal-detail', args=[self.ug.id])
        self.client.credentials(
            HTTP_AUTHORIZATION='Token ' + self.user.auth_token.key
        )
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(UserGoal.objects.filter(id=self.ug.id).count(), 0)


class TestUserBehaviorAPI(APITestCase):

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create(
            username="test",
            email="test@example.com",
        )
        self.goal = Goal.objects.create(
            title="Test Goal",
            subtitle="A subtitle",
            description="A Description",
            outcome="The outcome"
        )
        self.behavior = Behavior.objects.create(title="Test Behavior")
        self.behavior.goals.add(self.goal)
        self.behavior.save()

        self.ub = UserBehavior.objects.create(
            user=self.user,
            behavior=self.behavior,
        )

    def tearDown(self):
        User = get_user_model()
        User.objects.filter(id=self.user.id).delete()
        Goal.objects.filter(id=self.goal.id).delete()
        Behavior.objects.filter(id=self.behavior.id).delete()
        UserBehavior.objects.filter(id=self.ub.id).delete()

    def test_userbehavior_list(self):
        """Ensure un-authenticated requests don't expose any results."""
        url = reverse('userbehavior-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)

    def test_userbehavior_list_authenticated(self):
        """Ensure authenticated requests DO expose results."""
        url = reverse('userbehavior-list')
        self.client.credentials(
            HTTP_AUTHORIZATION='Token ' + self.user.auth_token.key
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['user'], self.user.id)
        self.assertEqual(
            response.data['results'][0]['behavior']['id'],
            self.behavior.id
        )
        self.assertEqual(
            response.data['results'][0]['behavior']['title'],
            self.behavior.title
        )

    def test_post_userbehavior_list_unathenticated(self):
        """Unauthenticated requests should not be allowed to post"""
        url = reverse('userbehavior-list')
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_userbehavior_list_athenticated(self):
        """Authenticated users Should be able to create a UserBehavior."""
        newbehavior = Behavior.objects.create(title="New")

        url = reverse('userbehavior-list')
        self.client.credentials(
            HTTP_AUTHORIZATION='Token ' + self.user.auth_token.key
        )
        response = self.client.post(url, {"behavior": newbehavior.id})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(UserBehavior.objects.filter(user=self.user).count(), 2)

        # Clean up.
        newbehavior.delete()

    def test_post_userbehavior_list_multiple_athenticated(self):
        """Authenticated users Should be able to create a multiple UserBehaviors."""
        behavior_a = Behavior.objects.create(title="New A")
        behavior_b = Behavior.objects.create(title="New B")

        url = reverse('userbehavior-list')
        self.client.credentials(
            HTTP_AUTHORIZATION='Token ' + self.user.auth_token.key
        )
        data = [{"behavior": behavior_a.id}, {"behavior": behavior_b.id}]
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(UserBehavior.objects.filter(user=self.user).count(), 3)

        # Clean up.
        behavior_a.delete()
        behavior_b.delete()

    def test_get_userbehavior_detail_unauthed(self):
        """Ensure unauthenticated users cannot view this endpoint."""
        url = reverse('userbehavior-detail', args=[self.ub.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_userbehavior_detail(self):
        """Ensure authenticated users can view this endpoint."""
        url = reverse('userbehavior-detail', args=[self.ub.id])
        self.client.credentials(
            HTTP_AUTHORIZATION='Token ' + self.user.auth_token.key
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_post_userbehavior_detail_not_allowed(self):
        """Ensure POSTing to the detail endpoint is not allowed."""
        url = reverse('userbehavior-detail', args=[self.ub.id])
        response = self.client.post(url, {'behavior': 1})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # Even if you're authenticated
        self.client.credentials(
            HTTP_AUTHORIZATION='Token ' + self.user.auth_token.key
        )
        response = self.client.post(url, {'behavior': 1})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_put_userbehavior_detail_not_allowed(self):
        """Ensure PUTing to the detail endpoint is not allowed."""
        url = reverse('userbehavior-detail', args=[self.ub.id])
        response = self.client.put(url, {'behavior': 1})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # Even if you're authenticated
        self.client.credentials(
            HTTP_AUTHORIZATION='Token ' + self.user.auth_token.key
        )
        response = self.client.put(url, {'behavior': 1})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_userbehavior_detail_unauthed(self):
        """Ensure unauthenticated users cannot delete."""
        url = reverse('userbehavior-detail', args=[self.ub.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_userbehavior_detail(self):
        """Ensure authenticated users can deelte."""
        url = reverse('userbehavior-detail', args=[self.ub.id])
        self.client.credentials(
            HTTP_AUTHORIZATION='Token ' + self.user.auth_token.key
        )
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(UserBehavior.objects.filter(id=self.ub.id).count(), 0)


class TestUserActionAPI(APITestCase):

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create(
            username="test",
            email="test@example.com",
        )
        self.goal = Goal.objects.create(
            title="Test Goal",
            subtitle="A subtitle",
            description="A Description",
            outcome="The outcome"
        )
        self.behavior = Behavior.objects.create(title="Test Action")
        self.behavior.goals.add(self.goal)
        self.behavior.save()

        self.action = Action.objects.create(
            title="Test Action",
            behavior=self.behavior
        )

        self.ua = UserAction.objects.create(
            user=self.user,
            action=self.action,
        )

    def tearDown(self):
        User = get_user_model()
        User.objects.filter(id=self.user.id).delete()
        Goal.objects.filter(id=self.goal.id).delete()
        Behavior.objects.filter(id=self.behavior.id).delete()
        Action.objects.filter(id=self.action.id).delete()
        UserAction.objects.filter(id=self.ua.id).delete()

    def test_get_useraction_list(self):
        """Ensure un-authenticated requests don't expose any results."""
        url = reverse('useraction-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)

    def test_get_useraction_list_authenticated(self):
        """Ensure authenticated requests DO expose results."""
        url = reverse('useraction-list')
        self.client.credentials(
            HTTP_AUTHORIZATION='Token ' + self.user.auth_token.key
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['user'], self.user.id)
        self.assertEqual(
            response.data['results'][0]['action']['id'],
            self.action.id
        )
        self.assertEqual(
            response.data['results'][0]['action']['title'],
            self.action.title
        )

    def test_post_useraction_list_unathenticated(self):
        """Unauthenticated requests should not be allowed to post"""
        url = reverse('useraction-list')
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_useraction_list_athenticated(self):
        """Authenticated users Should be able to create a UserAction."""
        newaction = Action.objects.create(title="New", behavior=self.behavior)

        url = reverse('useraction-list')
        self.client.credentials(
            HTTP_AUTHORIZATION='Token ' + self.user.auth_token.key
        )
        response = self.client.post(url, {"action": newaction.id})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(UserAction.objects.filter(user=self.user).count(), 2)

        # Clean up.
        newaction.delete()

    def test_post_useraction_list_multiple_athenticated(self):
        """Authenticated users should be able to create multiple UserActions."""
        action_a = Action.objects.create(title="Action A", behavior=self.behavior)
        action_b = Action.objects.create(title="Action B", behavior=self.behavior)

        url = reverse('useraction-list')
        self.client.credentials(
            HTTP_AUTHORIZATION='Token ' + self.user.auth_token.key
        )
        post_data = [{"action": action_a.id}, {"action": action_b.id}]
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(UserAction.objects.filter(user=self.user).count(), 3)

        # Clean up.
        action_a.delete()
        action_b.delete()

    def test_get_useraction_detail_unauthenticated(self):
        """Ensure unauthenticated users cannot view this endpoint."""
        url = reverse('useraction-detail', args=[self.ua.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_useraction_detail_authenticated(self):
        """Ensure authenticated users can view this endpoint."""
        url = reverse('useraction-detail', args=[self.ua.id])
        self.client.credentials(
            HTTP_AUTHORIZATION='Token ' + self.user.auth_token.key
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_post_useraction_detail_not_allowed(self):
        """Ensure POSTing to the detail endpoint is not allowed."""
        url = reverse('useraction-detail', args=[self.ua.id])
        response = self.client.post(url, {'action': 1})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # Even if you're authenticated
        self.client.credentials(
            HTTP_AUTHORIZATION='Token ' + self.user.auth_token.key
        )
        response = self.client.post(url, {'action': 1})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_put_useraction_detail_not_allowed(self):
        """Ensure PUTing to the detail endpoint is not allowed."""
        url = reverse('useraction-detail', args=[self.ua.id])
        response = self.client.put(url, {'action': 1})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # Even if you're authenticated
        self.client.credentials(
            HTTP_AUTHORIZATION='Token ' + self.user.auth_token.key
        )
        response = self.client.put(url, {'action': 1})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_useraction_detail_unauthenticated(self):
        """Ensure unauthenticated users cannot delete."""
        url = reverse('useraction-detail', args=[self.ua.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_useraction_detail_authenticated(self):
        """Ensure authenticated users can deelte."""
        url = reverse('useraction-detail', args=[self.ua.id])
        self.client.credentials(
            HTTP_AUTHORIZATION='Token ' + self.user.auth_token.key
        )
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(UserAction.objects.filter(id=self.ua.id).count(), 0)


class TestUserCategoryAPI(APITestCase):

    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create(
            username="test",
            email="test@example.com",
        )
        self.category = Category.objects.create(
            title="Test Category",
            order=1
        )
        # Assign a Category to the User
        self.uc = UserCategory.objects.create(user=self.user, category=self.category)

    def tearDown(self):
        User = get_user_model()
        User.objects.filter(id=self.user.id).delete()
        Category.objects.filter(id=self.category.id).delete()
        UserCategory.objects.filter(id=self.uc.id).delete()

    def test_get_usercategory_list_unauthenticated(self):
        """Ensure un-authenticated requests don't expose any results."""
        url = reverse('usercategory-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)

    def test_get_usercategory_list_authenticated(self):
        """Ensure authenticated requests DO expose results."""
        url = reverse('usercategory-list')
        self.client.credentials(
            HTTP_AUTHORIZATION='Token ' + self.user.auth_token.key
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

        # check the fields of a result object.
        self.assertIn("id", response.data['results'][0])
        self.assertIn("category", response.data['results'][0])
        self.assertIn("order", response.data['results'][0]['category'])
        self.assertIn("title", response.data['results'][0]['category'])
        self.assertIn("title_slug", response.data['results'][0]['category'])
        self.assertIn("description", response.data['results'][0]['category'])
        self.assertIn("icon_url", response.data['results'][0]['category'])

        self.assertEqual(
            response.data['results'][0]['id'],
            self.uc.id
        )
        self.assertEqual(
            response.data['results'][0]['category']['id'],
            self.category.id
        )
        self.assertEqual(
            response.data['results'][0]['category']['title'],
            self.category.title
        )

    def test_post_usercategory_list_unauthenticated(self):
        """POST should not be allowed for unauthenticated users"""
        url = reverse('usercategory-list')
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_usercategory_list_authenticated(self):
        """POST should be allowed for authenticated users"""
        newcat = Category.objects.create(order=2, title="NEW")

        url = reverse('usercategory-list')
        self.client.credentials(
            HTTP_AUTHORIZATION='Token ' + self.user.auth_token.key
        )
        response = self.client.post(url, {"category": newcat.id})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure our user has two categories.
        self.assertEqual(self.user.usercategory_set.count(), 2)

        # clean up.
        newcat.delete()

    def test_post_usercategory_list_multiple_authenticated(self):
        """POST should be allowed for authenticated users"""
        cat_a = Category.objects.create(order=2, title="A")
        cat_b = Category.objects.create(order=3, title="B")

        url = reverse('usercategory-list')
        self.client.credentials(
            HTTP_AUTHORIZATION='Token ' + self.user.auth_token.key
        )
        post_data = [
            {'category': cat_a.id},
            {'category': cat_b.id}
        ]
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure our user is associated with the categories.
        self.assertEqual(self.user.usercategory_set.count(), 3)

        # clean up.
        cat_a.delete()
        cat_b.delete()

    def test_get_usercategory_detail_unauthenticated(self):
        """Ensure unauthenticated users cannot view this endpoint."""
        url = reverse('usercategory-detail', args=[self.uc.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_usercategory_detail_authenticated(self):
        """Ensure authenticated users can view this endpoint."""
        url = reverse('usercategory-detail', args=[self.uc.id])
        self.client.credentials(
            HTTP_AUTHORIZATION='Token ' + self.user.auth_token.key
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_post_usercategory_detail_not_allowed(self):
        """Ensure POSTing to the detail endpoint is not allowed."""
        url = reverse('usercategory-detail', args=[self.uc.id])
        response = self.client.post(url, {'category': 1})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # Even if you're authenticated
        self.client.credentials(
            HTTP_AUTHORIZATION='Token ' + self.user.auth_token.key
        )
        response = self.client.post(url, {'category': 1})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_put_usercategory_detail_not_allowed(self):
        """Ensure PUTing to the detail endpoint is not allowed."""
        url = reverse('usercategory-detail', args=[self.uc.id])
        response = self.client.put(url, {'category': 1})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # Even if you're authenticated
        self.client.credentials(
            HTTP_AUTHORIZATION='Token ' + self.user.auth_token.key
        )
        response = self.client.put(url, {'category': 1})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_usercategory_detail_unauthenticated(self):
        """Ensure unauthenticated users cannot delete."""
        url = reverse('usercategory-detail', args=[self.uc.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_usercategory_detail_authenticated(self):
        """Ensure authenticated users can deelte."""
        url = reverse('usercategory-detail', args=[self.uc.id])
        self.client.credentials(
            HTTP_AUTHORIZATION='Token ' + self.user.auth_token.key
        )
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(UserCategory.objects.filter(id=self.uc.id).count(), 0)
