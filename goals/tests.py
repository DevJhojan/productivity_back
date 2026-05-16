import json
from decimal import Decimal

from django.test import TestCase, RequestFactory

from users.models_users import User, UserAttribute
from .models_goal import Goal
from .goal_service import (
    create_goal,
    get_goal,
    patch_goal,
    delete_goal,
    list_goals,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_user(username="goaluser", points=0.0):
    return User.objects.create_user(
        username=username,
        email=f"{username}@test.com",
        password="pass",
        document_number=username,
        points=points,
    )


def make_goal(owner, goal_subtype="weekly_goal", attribute=None, status=Goal.Status.PENDING):
    if attribute is None:
        attribute = owner.attributes.get(name=UserAttribute.AttributeName.STRENGTH)
    return Goal.objects.create(
        owner=owner,
        attribute=attribute,
        title="Test goal",
        goal_subtype=goal_subtype,
        status=status,
    )


def post_request(factory, path, body):
    return factory.post(path, json.dumps(body), content_type="application/json")


def patch_request(factory, path, body):
    return factory.patch(path, json.dumps(body), content_type="application/json")


# ── Create goal ───────────────────────────────────────────────────────────────

class CreateGoalTest(TestCase):
    def setUp(self):
        self.owner = make_user()
        self.factory = RequestFactory()

    def test_creates_goal_with_default_attribute(self):
        req = post_request(self.factory, "/api/goals/", {
            "owner_id": self.owner.id,
            "title": "Finish book",
            "goal_subtype": "weekly_goal",
        })
        response = create_goal(req)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.content)
        self.assertEqual(data["title"], "Finish book")
        self.assertEqual(data["goal_subtype"], "weekly_goal")
        self.assertEqual(data["attribute"]["name"], UserAttribute.AttributeName.STRENGTH)

    def test_creates_goal_with_explicit_attribute(self):
        attr = self.owner.attributes.get(name=UserAttribute.AttributeName.INTELLIGENCE)
        req = post_request(self.factory, "/api/goals/", {
            "owner_id": self.owner.id,
            "title": "Learn Django",
            "goal_subtype": "monthly_project",
            "attribute_id": attr.id,
        })
        response = create_goal(req)
        data = json.loads(response.content)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(data["attribute"]["name"], UserAttribute.AttributeName.INTELLIGENCE)

    def test_create_without_goal_subtype_returns_400(self):
        req = post_request(self.factory, "/api/goals/", {
            "owner_id": self.owner.id,
            "title": "No subtype",
        })
        response = create_goal(req)
        self.assertEqual(response.status_code, 400)

    def test_create_with_invalid_goal_subtype_returns_400(self):
        req = post_request(self.factory, "/api/goals/", {
            "owner_id": self.owner.id,
            "title": "Bad subtype",
            "goal_subtype": "invalid_type",
        })
        response = create_goal(req)
        self.assertEqual(response.status_code, 400)

    def test_create_without_title_returns_400(self):
        req = post_request(self.factory, "/api/goals/", {
            "owner_id": self.owner.id,
            "goal_subtype": "weekly_goal",
        })
        response = create_goal(req)
        self.assertEqual(response.status_code, 400)

    def test_cross_owner_attribute_returns_400(self):
        other = make_user(username="other_goal")
        foreign_attr = other.attributes.get(name=UserAttribute.AttributeName.STRENGTH)
        req = post_request(self.factory, "/api/goals/", {
            "owner_id": self.owner.id,
            "title": "Bad attr",
            "goal_subtype": "weekly_goal",
            "attribute_id": foreign_attr.id,
        })
        response = create_goal(req)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn("owner", data["error"])


# ── Complete goal — points per subtype ────────────────────────────────────────

class CompleteGoalPointsTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _complete_goal(self, owner, goal):
        req = patch_request(self.factory, f"/api/goals/{goal.id}/", {"status": "COMPLETED"})
        return patch_goal(req, goal.id), owner, goal

    def test_weekly_goal_earns_100(self):
        owner = make_user(username="u_weekly")
        goal = make_goal(owner, goal_subtype="weekly_goal")
        attr = goal.attribute

        response, owner, goal = self._complete_goal(owner, goal)
        data = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["earned_points"], 1.00)
        attr.refresh_from_db()
        self.assertEqual(attr.points, Decimal("1.00"))

    def test_monthly_project_earns_500(self):
        owner = make_user(username="u_monthly")
        goal = make_goal(owner, goal_subtype="monthly_project")
        attr = goal.attribute

        response, owner, goal = self._complete_goal(owner, goal)
        data = json.loads(response.content)

        self.assertEqual(data["earned_points"], 5.00)
        attr.refresh_from_db()
        self.assertEqual(attr.points, Decimal("5.00"))

    def test_annual_project_earns_1500(self):
        owner = make_user(username="u_annual")
        goal = make_goal(owner, goal_subtype="annual_project")
        attr = goal.attribute

        response, owner, goal = self._complete_goal(owner, goal)
        data = json.loads(response.content)

        self.assertEqual(data["earned_points"], 15.00)
        attr.refresh_from_db()
        self.assertEqual(attr.points, Decimal("15.00"))

    def test_five_year_project_earns_3000(self):
        owner = make_user(username="u_5year")
        goal = make_goal(owner, goal_subtype="five_year_project")
        attr = goal.attribute

        response, owner, goal = self._complete_goal(owner, goal)
        data = json.loads(response.content)

        self.assertEqual(data["earned_points"], 30.00)
        attr.refresh_from_db()
        self.assertEqual(attr.points, Decimal("30.00"))

    def test_complete_recalculates_owner_points(self):
        owner = make_user(username="u_recalc")
        goal = make_goal(owner, goal_subtype="weekly_goal")

        req = patch_request(self.factory, f"/api/goals/{goal.id}/", {"status": "COMPLETED"})
        patch_goal(req, goal.id)

        owner.refresh_from_db()
        # 1.00 in Strength / 5 attrs = 0.20
        self.assertEqual(float(owner.points), 0.20)

    def test_complete_sets_completed_at(self):
        owner = make_user(username="u_ts")
        goal = make_goal(owner, goal_subtype="weekly_goal")

        req = patch_request(self.factory, f"/api/goals/{goal.id}/", {"status": "COMPLETED"})
        patch_goal(req, goal.id)

        goal.refresh_from_db()
        self.assertIsNotNone(goal.completed_at)

    def test_complete_includes_level_result(self):
        owner = make_user(username="u_lvl")
        goal = make_goal(owner, goal_subtype="weekly_goal")

        req = patch_request(self.factory, f"/api/goals/{goal.id}/", {"status": "COMPLETED"})
        response = patch_goal(req, goal.id)
        data = json.loads(response.content)

        self.assertIn("level_result", data)
        self.assertIn("owner_points", data)

    def test_already_completed_does_not_award_again(self):
        owner = make_user(username="u_double")
        goal = make_goal(owner, goal_subtype="weekly_goal", status=Goal.Status.COMPLETED)
        attr = goal.attribute
        attr.points = Decimal("1.00")
        attr.save()

        req = patch_request(self.factory, f"/api/goals/{goal.id}/", {"status": "COMPLETED"})
        patch_goal(req, goal.id)

        attr.refresh_from_db()
        self.assertEqual(attr.points, Decimal("1.00"))

    def test_patch_non_status_field_does_not_award_points(self):
        owner = make_user(username="u_notitle")
        goal = make_goal(owner, goal_subtype="weekly_goal")

        req = patch_request(self.factory, f"/api/goals/{goal.id}/", {"title": "New title"})
        response = patch_goal(req, goal.id)
        data = json.loads(response.content)

        self.assertNotIn("earned_points", data)
        owner.refresh_from_db()
        self.assertEqual(float(owner.points), 0.0)


# ── Delete goal ───────────────────────────────────────────────────────────────

class DeleteGoalTest(TestCase):
    def setUp(self):
        self.owner = make_user(username="u_del")
        self.goal = make_goal(self.owner)
        self.factory = RequestFactory()

    def test_delete_goal(self):
        req = self.factory.delete(f"/api/goals/{self.goal.id}/")
        response = delete_goal(req, self.goal.id)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Goal.objects.filter(id=self.goal.id).exists())

    def test_delete_nonexistent_goal_returns_404(self):
        req = self.factory.delete("/api/goals/99999/")
        response = delete_goal(req, 99999)
        self.assertEqual(response.status_code, 404)


# ── List goals ────────────────────────────────────────────────────────────────

class ListGoalsTest(TestCase):
    def setUp(self):
        self.owner = make_user(username="u_list1")
        self.other = make_user(username="u_list2")
        make_goal(self.owner, goal_subtype="weekly_goal")
        make_goal(self.owner, goal_subtype="annual_project")
        make_goal(self.other, goal_subtype="monthly_project")
        self.factory = RequestFactory()

    def test_list_all_goals(self):
        req = self.factory.get("/api/goals/")
        response = list_goals(req)
        data = json.loads(response.content)
        self.assertEqual(len(data), 3)

    def test_filter_by_owner_id(self):
        req = self.factory.get(f"/api/goals/?owner_id={self.owner.id}")
        response = list_goals(req)
        data = json.loads(response.content)
        self.assertEqual(len(data), 2)
        self.assertTrue(all(g["owner_id"] == self.owner.id for g in data))
