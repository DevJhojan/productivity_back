class LevelSystem:
    LEVEL_TIERS = [
        {
            "level": "Nobody",
            "icon": "👤",
            "min": 0,
            "max": 499,
            "global_min": 99.0,
            "global_max": 90.9,
        },
        {
            "level": "Forgotten",
            "icon": "🕳️",
            "min": 500,
            "max": 1499,
            "global_min": 90.0,
            "global_max": 81.0,
        },
        {
            "level": "Novice",
            "icon": "🌱",
            "min": 1500,
            "max": 3999,
            "global_min": 80.0,
            "global_max": 70.1,
        },
        {
            "level": "Apprentice",
            "icon": "📘",
            "min": 4000,
            "max": 9999,
            "global_min": 75.0,
            "global_max": 69.6,
        },
        {
            "level": "Known",
            "icon": "👀",
            "min": 10000,
            "max": 24999,
            "global_min": 60.0,
            "global_max": 46.5,
        },
        {
            "level": "Respected",
            "icon": "🛡️",
            "min": 25000,
            "max": 59999,
            "global_min": 40.0,
            "global_max": 17.5,
        },
        {
            "level": "Influential",
            "icon": "📣",
            "min": 60000,
            "max": 119999,
            "global_min": 20.0,
            "global_max": 2.0,
        },
        {
            "level": "Master",
            "icon": "🧙",
            "min": 120000,
            "max": 199999,
            "global_min": 10.0,
            "global_max": 2.8,
        },
        {
            "level": "Legendary",
            "icon": "🗡️",
            "min": 200000,
            "max": 349999,
            "global_min": 5.0,
            "global_max": 1.4,
        },
        {
            "level": "Supreme",
            "icon": "🌌",
            "min": 350000,
            "max": 499999,
            "global_min": 2.0,
            "global_max": 1.1,
        },
        {
            "level": "Godlike",
            "icon": "✨👑",
            "min": 500000,
            "max": 500000,
            "global_min": 1.0,
            "global_max": 1.0,
        },
    ]

    @classmethod
    def clamp_points(
        cls, points: float, min_points: float = 0, max_points: float = 500000
    ) -> float:
        return max(min_points, min(points, max_points))

    @classmethod
    def find_tier(cls, points: float) -> tuple[int, dict]:
        for index, tier in enumerate(cls.LEVEL_TIERS, start=1):
            if tier["min"] <= points <= tier["max"]:
                return index, tier
        return len(cls.LEVEL_TIERS), cls.LEVEL_TIERS[-1]

    @classmethod
    def calculate_progress(cls, points: float, tier: dict) -> float:
        if tier["min"] == tier["max"]:
            return 1.0
        return (points - tier["min"]) / (tier["max"] - tier["min"])

    @classmethod
    def calculate_star(cls, progress: float) -> int:
        return min(10, max(1, int(progress * 10) + 1))

    @classmethod
    def calculate_global_system(cls, progress: float, tier: dict) -> float:
        value = (
            tier["global_min"] + (tier["global_max"] - tier["global_min"]) * progress
        )
        return round(value, 2)

    @classmethod
    def get_next_level(cls, index: int) -> str | None:
        if index >= len(cls.LEVEL_TIERS):
            return None
        return cls.LEVEL_TIERS[index]["level"]

    @classmethod
    def build_level_state(cls, points: float) -> dict:
        points = cls.clamp_points(points)
        order, tier = cls.find_tier(points)
        progress = cls.calculate_progress(points, tier)

        if tier["min"] == tier["max"]:
            star = 10
            global_system = tier["global_max"]
        else:
            star = cls.calculate_star(progress)
            global_system = cls.calculate_global_system(progress, tier)

        return {
            "points": round(points, 2),
            "level": tier["level"],
            "icon": tier["icon"],
            "star": star,
            "order": order,
            "global_system": global_system,
            "level_progress": round(progress * 100, 2),
            "next_level": cls.get_next_level(order),
        }

    @classmethod
    def compare_level_states(cls, previous_state: dict, current_state: dict) -> str:
        if current_state["order"] > previous_state["order"]:
            return "leveled_up"
        if current_state["order"] < previous_state["order"]:
            return "leveled_down"
        if current_state["star"] > previous_state["star"]:
            return "star_up"
        if current_state["star"] < previous_state["star"]:
            return "star_down"
        return "no_change"

    @classmethod
    def handle_level_change(
        cls, current_points: float, previous_points: float | None = None
    ) -> dict:
        current_state = cls.build_level_state(current_points)

        if previous_points is None:
            return current_state

        previous_state = cls.build_level_state(previous_points)
        change = cls.compare_level_states(previous_state, current_state)

        return {
            "change": change,
            "previous": previous_state,
            "current": current_state,
        }

    @classmethod
    def get_points_from_rules(
        cls,
        task_type: str,
        habit_day: int | None = None,
    ) -> float:
        if task_type == "daily_action":
            return 0.10

        if task_type == "habit":
            if habit_day is None:
                raise ValueError("habit_day is required when task_type is 'habit'.")
            if habit_day == 365:
                return 3.65
            if habit_day == 100:
                return 1.00
            if habit_day == 10:
                return 0.10
            return 0.01

        if task_type == "weekly_goal":
            return 1.00

        if task_type == "monthly_project":
            return 5.00

        if task_type == "annual_project":
            return 15.00

        if task_type == "five_year_project":
            return 30.00

        raise ValueError("Invalid task_type.")

    @classmethod
    def complete_task_with_rules(
        cls,
        current_points: float,
        task_type: str,
        habit_day: int | None = None,
    ) -> dict:
        previous_points = cls.clamp_points(current_points)
        earned_points = cls.get_points_from_rules(
            task_type=task_type, habit_day=habit_day
        )
        new_points = cls.clamp_points(previous_points + earned_points)

        level_result = cls.handle_level_change(
            current_points=new_points,
            previous_points=previous_points,
        )

        return {
            "task_completed": True,
            "task_type": task_type,
            "earned_points": earned_points,
            "total_points": round(new_points, 2),
            "level_result": level_result,
        }
