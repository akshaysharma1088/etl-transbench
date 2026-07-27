-- Legacy analytical SQL: sessionize user events.
-- A new session starts when the gap from the previous event of the SAME
-- user is STRICTLY GREATER than 30 minutes (gap == 30:00 stays in-session).
-- Within a user, events are ordered by event_ts, then event_id (tiebreak).
-- Output user_sessions: user_id, session_num (1-based per user),
--   session_start, session_end, event_count.
SELECT user_id,
       SUM(new_sess) OVER (PARTITION BY user_id ORDER BY event_ts, event_id
                           ROWS UNBOUNDED PRECEDING) AS session_num, ...
FROM ( SELECT *, CASE WHEN event_ts - LAG(event_ts) OVER
             (PARTITION BY user_id ORDER BY event_ts, event_id)
             > INTERVAL '30' MINUTE OR LAG(event_ts) ... IS NULL
             THEN 1 ELSE 0 END AS new_sess FROM events ) t
GROUP BY user_id, session_num;
