SELECT
    team,
    count() AS work_items,
    countIf(blocked = 1) AS blocked_items,
    round(100 * avg(blocked), 1) AS blocked_pct,
    round(avg(actual_hours / planned_hours), 2) AS avg_effort_ratio,
    countIf(status = 'done' AND completed_at > due_at) AS late_completed,
    countIf(status = 'done') AS completed
FROM agentic_analytics.delivery_work_items
GROUP BY team
ORDER BY team;
