CREATE DATABASE IF NOT EXISTS agentic_analytics;

CREATE TABLE IF NOT EXISTS agentic_analytics.delivery_work_items
(
    work_item_id String,
    team LowCardinality(String),
    priority LowCardinality(String),
    status LowCardinality(String),
    created_at DateTime,
    due_at DateTime,
    completed_at Nullable(DateTime),
    planned_hours UInt16,
    actual_hours Float32,
    blocked UInt8,
    blocker_type LowCardinality(String),
    rework_count UInt8,
    customer_impact UInt8
)
ENGINE = MergeTree
ORDER BY (team, created_at, work_item_id);
