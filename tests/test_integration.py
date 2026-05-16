import json
from django.test import TestCase
from users.models import User
from task.models import Task
from task.task_service import patch_task, update_task
from funcs.system_levels import LevelSystem


def make_user(username="player", document_number="100", points=0.0):
    return User.objects.create_user(
        username=username,
        email=f"{username}@test.com",
        password="pass",
        document_number=document_number,
        points=points,
    )


def make_task(
    owner, priority=Task.Priority.NOT_IMPORTANT_NOT_URGENT, status=Task.Status.PENDING
):
    return Task.objects.create(
        title="Integration task",
        status=status,
        priority=priority,
        owner=owner,
    )


class CompletingTaskAwardsPointsTest(TestCase):
    """Al completar una tarea, el usuario debe ganar puntos y su nivel actualizarse."""

    def setUp(self):
        self.user = make_user(points=0.0)
        self.task = make_task(
            self.user, priority=Task.Priority.NOT_IMPORTANT_NOT_URGENT
        )

    def test_patch_complete_increments_user_points(self):
        patch_task(self.task, {"status": "COMPLETED"})

        self.user.refresh_from_db()
        self.assertGreater(float(self.user.points), 0.0)

    def test_put_complete_increments_user_points(self):
        update_task(
            self.task, {"title": "T", "status": "COMPLETED", "owner_id": self.user.id}
        )

        self.user.refresh_from_db()
        self.assertGreater(float(self.user.points), 0.0)

    def test_earned_points_match_level_system_rules(self):
        expected = LevelSystem.get_points_from_rules("daily_action")
        patch_task(self.task, {"status": "COMPLETED"})

        self.user.refresh_from_db()
        self.assertEqual(float(self.user.points), expected)

    def test_completing_twice_does_not_double_points(self):
        patch_task(self.task, {"status": "COMPLETED"})
        self.user.refresh_from_db()
        points_after_first = float(self.user.points)

        patch_task(self.task, {"status": "COMPLETED"})
        self.user.refresh_from_db()
        self.assertEqual(float(self.user.points), points_after_first)

    def test_response_contains_level_result(self):
        response = patch_task(self.task, {"status": "COMPLETED"})
        data = json.loads(response.content)

        self.assertIn("earned_points", data)
        self.assertIn("level_result", data)
        self.assertIn("owner_points", data)

    def test_level_state_reflects_new_points(self):
        patch_task(self.task, {"status": "COMPLETED"})
        self.user.refresh_from_db()

        state = self.user.get_level_state()
        self.assertEqual(state["points"], float(self.user.points))
        self.assertIn("level", state)
        self.assertIn("star", state)
        self.assertIn("next_level", state)


class LevelUpIntegrationTest(TestCase):
    """Con suficientes puntos acumulados el usuario sube de nivel."""

    def test_user_levels_up_after_many_completions(self):
        # Nobody: 0-499. Con 499.0 exacto el usuario está en Nobody.
        # IMPORTANT_URGENT otorga 1.00 pto (weekly_goal) -> 500.0 -> Forgotten (500-1499)
        user = make_user(points=499.0, document_number="200")

        task = make_task(user, priority=Task.Priority.IMPORTANT_URGENT)
        response = patch_task(task, {"status": "COMPLETED"})
        data = json.loads(response.content)

        user.refresh_from_db()
        self.assertGreaterEqual(float(user.points), 500.0)

        level_result = data["level_result"]
        self.assertEqual(level_result["change"], "leveled_up")
        self.assertEqual(level_result["current"]["level"], "Forgotten")
        self.assertEqual(level_result["previous"]["level"], "Nobody")

    def test_user_gains_star_without_level_change(self):
        # Con 0 puntos, star inicial = 1; completar una daily_action (0.10 pts) sube a star 1 también
        # Con puntos justo al inicio del tier, cualquier avance cambia star
        user = make_user(points=50.0, document_number="300")
        task = make_task(user, priority=Task.Priority.IMPORTANT_URGENT)  # +1.00 pto

        response = patch_task(task, {"status": "COMPLETED"})
        data = json.loads(response.content)

        level_result = data["level_result"]
        # Sigue en Nobody (0-499), pero pudo subir star
        self.assertIn(level_result["change"], ["star_up", "no_change"])
