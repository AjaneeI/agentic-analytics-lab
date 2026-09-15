import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

SEED = 42
ROWS = 500

random.seed(SEED)

teams = ["Platform", "Data", "Product", "AI"]
priorities = ["low", "medium", "high", "critical"]
statuses = ["done", "in_progress", "blocked"]
blocker_types = ["dependency", "technical", "requirements", "staffing", "none"]

out = Path("data/delivery_work_items.csv")
out.parent.mkdir(exist_ok=True)

start = datetime(2026, 1, 1)

fields = [
    "work_item_id",
    "team",
    "priority",
    "status",
    "created_at",
    "due_at",
    "completed_at",
    "planned_hours",
    "actual_hours",
    "blocked",
    "blocker_type",
    "rework_count",
    "customer_impact",
]

with out.open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()

    for i in range(1, ROWS + 1):
        created = start + timedelta(days=random.randint(0, 180))
        planned = random.randint(4, 80)

        blocked = random.random() < 0.18
        blocker = random.choice(blocker_types[:-1]) if blocked else "none"

        actual_multiplier = random.uniform(0.7, 1.4)
        if blocked:
            actual_multiplier += random.uniform(0.2, 0.8)

        actual = round(planned * actual_multiplier, 1)

        due = created + timedelta(hours=planned * random.uniform(1.5, 3))

        status = random.choices(
            statuses,
            weights=[0.65, 0.25, 0.10],
            k=1,
        )[0]

        completed = (
            created + timedelta(hours=actual * random.uniform(1.2, 2.5))
            if status == "done"
            else None
        )

        writer.writerow(
            {
                "work_item_id": f"WI-{i:04d}",
                "team": random.choice(teams),
                "priority": random.choice(priorities),
                "status": status,
                "created_at": created.strftime("%Y-%m-%d %H:%M:%S"),
                "due_at": due.strftime("%Y-%m-%d %H:%M:%S"),
                "completed_at": completed.strftime("%Y-%m-%d %H:%M:%S") if completed else "",
                "planned_hours": planned,
                "actual_hours": actual,
                "blocked": int(blocked),
                "blocker_type": blocker,
                "rework_count": random.choices(
                    [0, 1, 2, 3],
                    weights=[0.60, 0.25, 0.10, 0.05],
                    k=1,
                )[0],
                "customer_impact": random.randint(1, 5),
            }
        )

print(f"Generated {ROWS} rows at {out}")
