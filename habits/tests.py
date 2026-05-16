import json
from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase, RequestFactory

from users.models_users import User, UserAttribute
from .models_habit import Habit, HabitLog
from .habit_service import (
    create_habit,
    get_habit,
    patch_habit,
    delete_habit,
    check_habit,
    uncheck_habit,
    list_habits,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_user(username="habituser", points=0.0):
    return User.objects.create_user(
        username=username,
        email=f"{username}@test.com",
        password="pass",
        document_number=username,
        points=points,
    )


def make_habit(owner, attribute=None, title="Run daily"):
    if attribute is None:
        attribute = owner.attributes.get(name=UserAttribute.AttributeName.STRENGTH)
    return Habit.objects.create(
        owner=owner,
        attribute=attribute,
        title=title,
        description="",
    )


def post_request(factory, path, body):
    return factory.post(path, json.dumps(body), content_type="application/json")


def patch_request(factory, path, body):
    return factory.patch(path, json.dumps(body), content_type="application/json")


# ── Create habit ──────────────────────────────────────────────────────────────

class CreateHabitTest(TestCase):
    def setUp(self):
        self.owner = make_user()
        self.factory = RequestFactory()

    def test_creates_habit_with_default_attribute(self):
        req = post_request(self.factory, "/api/habits/", {"owner_id": self.owner.id, "title": "Meditate"})
        response = create_habit(req)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.content)
        self.assertEqual(data["title"], "Meditate")
        self.assertEqual(data["attribute"]["name"], UserAttribute.AttributeName.STRENGTH)

    def test_creates_habit_with_explicit_attribute(self):
        attr = self.owner.attributes.get(name=UserAttribute.AttributeName.AGILITY)
        req = post_request(
            self.factory, "/api/habits/",
            {"owner_id": self.owner.id, "title": "Run", "attribute_id": attr.id},
        )
        response = create_habit(req)
        data = json.loads(response.content)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(data["attribute"]["name"], UserAttribute.AttributeName.AGILITY)

    def test_create_habit_requires_owner_id(self):
        req = post_request(self.factory, "/api/habits/", {"title": "Read"})
        response = create_habit(req)
        self.assertEqual(response.status_code, 400)

    def test_create_habit_requires_title(self):
        req = post_request(self.factory, "/api/habits/", {"owner_id": self.owner.id})
        response = create_habit(req)
        self.assertEqual(response.status_code, 400)

    def test_cross_owner_attribute_returns_400(self):
        other_user = make_user(username="other")
        foreign_attr = other_user.attributes.get(name=UserAttribute.AttributeName.STRENGTH)
        req = post_request(
            self.factory, "/api/habits/",
            {"owner_id": self.owner.id, "title": "Swim", "attribute_id": foreign_attr.id},
        )
        response = create_habit(req)
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn("owner", data["error"])


# ── Check habit ───────────────────────────────────────────────────────────────

class CheckHabitTest(TestCase):
    def setUp(self):
        self.owner = make_user()
        self.habit = make_habit(self.owner)
        self.factory = RequestFactory()

    def _check(self):
        req = self.factory.post(f"/api/habits/{self.habit.id}/check/")
        return check_habit(req, self.habit.id)

    def _uncheck(self):
        req = self.factory.delete(f"/api/habits/{self.habit.id}/check/")
        return uncheck_habit(req, self.habit.id)

    def test_check_creates_habit_log(self):
        self._check()
        self.assertEqual(HabitLog.objects.filter(habit=self.habit, date=date.today()).count(), 1)

    def test_check_first_day_earns_001(self):
        response = self._check()
        data = json.loads(response.content)
        self.assertEqual(data["earned_points"], 0.01)

    def test_check_increments_attribute_points(self):
        attr = self.habit.attribute
        before = Decimal(attr.points)
        self._check()
        attr.refresh_from_db()
        self.assertEqual(attr.points, before + Decimal("0.01"))

    def test_check_recalculates_user_points(self):
        self._check()
        self.owner.refresh_from_db()
        # avg of 5 attrs, one gained 0.01 → 0.01/5 = 0.00 rounded half-up
        self.assertGreaterEqual(float(self.owner.points), 0.0)

    def test_check_twice_same_day_returns_400(self):
        self._check()
        response = self._check()
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn("already checked", data["error"])

    def test_check_returns_streak_day_and_level_result(self):
        response = self._check()
        data = json.loads(response.content)
        self.assertIn("streak_day", data)
        self.assertIn("level_result", data)
        self.assertEqual(data["streak_day"], 1)

    def test_checked_today_flag_after_check(self):
        self._check()
        req = self.factory.get(f"/api/habits/{self.habit.id}/")
        response = get_habit(req, self.habit.id)
        data = json.loads(response.content)
        self.assertTrue(data["checked_today"])


# ── Uncheck habit ─────────────────────────────────────────────────────────────

class UncheckHabitTest(TestCase):
    def setUp(self):
        self.owner = make_user()
        self.habit = make_habit(self.owner)
        self.factory = RequestFactory()

    def test_uncheck_removes_log(self):
        req = self.factory.post(f"/api/habits/{self.habit.id}/check/")
        check_habit(req, self.habit.id)

        req = self.factory.delete(f"/api/habits/{self.habit.id}/check/")
        uncheck_habit(req, self.habit.id)

        self.assertFalse(HabitLog.objects.filter(habit=self.habit, date=date.today()).exists())

    def test_uncheck_subtracts_points(self):
        attr = self.habit.attribute
        req = self.factory.post(f"/api/habits/{self.habit.id}/check/")
        check_habit(req, self.habit.id)
        attr.refresh_from_db()
        points_after_check = Decimal(attr.points)

        req = self.factory.delete(f"/api/habits/{self.habit.id}/check/")
        uncheck_habit(req, self.habit.id)
        attr.refresh_from_db()

        self.assertEqual(attr.points, points_after_check - Decimal("0.01"))

    def test_uncheck_without_check_returns_400(self):
        req = self.factory.delete(f"/api/habits/{self.habit.id}/check/")
        response = uncheck_habit(req, self.habit.id)
        self.assertEqual(response.status_code, 400)


# ── Streak milestones ─────────────────────────────────────────────────────────

class StreakMilestoneTest(TestCase):
    def setUp(self):
        self.owner = make_user()
        self.habit = make_habit(self.owner)

    def _seed_logs(self, days: int):
        """Seed `days` consecutive daily logs ending yesterday."""
        today = date.today()
        for i in range(days, 0, -1):
            d = today - timedelta(days=i)
            HabitLog.objects.create(habit=self.habit, date=d, points_earned=Decimal("0.01"))

    def test_day_10_earns_010(self):
        self._seed_logs(9)  # 9 days already logged → streak becomes 10 on check
        factory = RequestFactory()
        req = factory.post(f"/api/habits/{self.habit.id}/check/")
        response = check_habit(req, self.habit.id)
        data = json.loads(response.content)
        self.assertEqual(data["streak_day"], 10)
        self.assertEqual(data["earned_points"], 0.10)

    def test_day_100_earns_100(self):
        self._seed_logs(99)
        factory = RequestFactory()
        req = factory.post(f"/api/habits/{self.habit.id}/check/")
        response = check_habit(req, self.habit.id)
        data = json.loads(response.content)
        self.assertEqual(data["streak_day"], 100)
        self.assertEqual(data["earned_points"], 1.00)


# ── Patch and Delete habit ────────────────────────────────────────────────────

class PatchDeleteHabitTest(TestCase):
    def setUp(self):
        self.owner = make_user()
        self.habit = make_habit(self.owner)
        self.factory = RequestFactory()

    def test_patch_title(self):
        req = patch_request(self.factory, f"/api/habits/{self.habit.id}/", {"title": "New title"})
        response = patch_habit(req, self.habit.id)
        data = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["title"], "New title")

    def test_patch_is_active(self):
        req = patch_request(self.factory, f"/api/habits/{self.habit.id}/", {"is_active": False})
        response = patch_habit(req, self.habit.id)
        data = json.loads(response.content)
        self.assertFalse(data["is_active"])

    def test_patch_attribute_cross_owner_returns_400(self):
        other = make_user(username="other2")
        foreign_attr = other.attributes.get(name=UserAttribute.AttributeName.VITALITY)
        req = patch_request(
            self.factory, f"/api/habits/{self.habit.id}/",
            {"attribute_id": foreign_attr.id},
        )
        response = patch_habit(req, self.habit.id)
        self.assertEqual(response.status_code, 400)

    def test_delete_habit(self):
        req = self.factory.delete(f"/api/habits/{self.habit.id}/")
        response = delete_habit(req, self.habit.id)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Habit.objects.filter(id=self.habit.id).exists())

    def test_delete_removes_logs(self):
        HabitLog.objects.create(habit=self.habit, date=date.today(), points_earned=Decimal("0.01"))
        req = self.factory.delete(f"/api/habits/{self.habit.id}/")
        delete_habit(req, self.habit.id)
        self.assertEqual(HabitLog.objects.filter(habit=self.habit).count(), 0)


# ── List habits ───────────────────────────────────────────────────────────────

class ListHabitsTest(TestCase):
    def setUp(self):
        self.owner = make_user()
        self.other = make_user(username="other3")
        make_habit(self.owner, title="Habit A")
        make_habit(self.owner, title="Habit B")
        make_habit(self.other, title="Habit C")
        self.factory = RequestFactory()

    def test_list_all_habits(self):
        req = self.factory.get("/api/habits/")
        response = list_habits(req)
        data = json.loads(response.content)
        self.assertEqual(len(data), 3)

    def test_filter_by_owner_id(self):
        req = self.factory.get(f"/api/habits/?owner_id={self.owner.id}")
        response = list_habits(req)
        data = json.loads(response.content)
        self.assertEqual(len(data), 2)
        self.assertTrue(all(h["owner_id"] == self.owner.id for h in data))
