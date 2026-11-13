-- 快照库（P2）：一天一版或多次修订，payload 为完整快照 JSON
CREATE TABLE IF NOT EXISTS briefing_day (
    day        date        NOT NULL,
    revision   integer     NOT NULL CHECK (revision >= 1),
    payload    jsonb       NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (day, revision)
);

COMMENT ON TABLE briefing_day IS '每日看板快照，按 day+revision 不可变追加';
COMMENT ON COLUMN briefing_day.payload IS '指数/股池/个股/异动的完整快照';

-- 任务审计：为补跑与告警提供依据
CREATE TABLE IF NOT EXISTS job_run (
    id          bigserial   PRIMARY KEY,
    job         text        NOT NULL,
    day         date        NOT NULL,
    started_at  timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    status      text        NOT NULL CHECK (status IN ('running', 'ok', 'failed')),
    detail      jsonb
);

CREATE INDEX IF NOT EXISTS idx_job_run_job_day ON job_run (job, day);
