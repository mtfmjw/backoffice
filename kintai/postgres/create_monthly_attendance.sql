CREATE OR REPLACE PROCEDURE create_monthly_attendance(
    IN p_member_id INT,
    IN p_month DATE,
    IN p_login_username VARCHAR(150),
    INOUT p_attendance_id INT DEFAULT 0
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_work_pattern_id INT;
BEGIN
    -- 1. Resolve work_pattern_id (member level -> organization fallback)
    SELECT COALESCE(mb.work_pattern_id, org.work_pattern_id, wp.id)
    INTO v_work_pattern_id
    FROM member mb
    LEFT JOIN organization org ON org.id = mb.organization_id
    LEFT JOIN work_pattern wp
    on wp.name = '所定'
    WHERE mb.id = p_member_id
    LIMIT 1;

    -- 2. Create the parent monthly attendance record
    INSERT INTO attendance_monthly (
        valid_flag,
        created_at,
        created_by,
        updated_at,
        updated_by,
        date,
        approve_status,
        member_id,
        work_pattern_id
    )
    VALUES (
        TRUE,
        CURRENT_TIMESTAMP,
        p_login_username,
        CURRENT_TIMESTAMP,
        p_login_username,
        p_month,
        0,
        p_member_id,
        v_work_pattern_id
    )
    RETURNING id INTO p_attendance_id;

    -- 3. Bulk insert all daily records for the given month
    WITH days AS (
        SELECT day::DATE AS day_date
        FROM generate_series(
            p_month, 
            (p_month + INTERVAL '1 month' - INTERVAL '1 day'), 
            INTERVAL '1 day'
        ) AS day
    ), 
    day_info AS (
        SELECT 
            d.day_date,
            EXTRACT(DOW FROM d.day_date) AS day_of_week,
            case when h.date = d.day_date then true else false end AS is_holiday,
            case when h.date - INTERVAL '1 day' = d.day_date then true else false end as is_substitute_holiday,
            case when h.date = d.day_date or h.date - INTERVAL '1 day' = d.day_date or EXTRACT(DOW FROM d.day_date) in (0, 6) then true else false end as day_off
        FROM days d
        LEFT JOIN holiday h ON h.date = d.day_date
    )
    INSERT INTO attendance_daily (
        date, 
        monthly_attendance_id, 
        work_pattern_id, 
        date_type,
        date_status,
        clock_in_time, 
        clock_out_time,
        has_lunch_break,
        has_break1,
        has_break2,
        has_break3,
        has_break4,
        has_break5
    )
    SELECT 
        d.day_date, 
        p_attendance_id, 
        v_work_pattern_id,
        CASE WHEN d.is_holiday THEN 3 -- 祝日
             WHEN d.is_substitute_holiday THEN 4 -- 振替休日
             WHEN d.day_of_week = 0 THEN 2 -- 日曜日、法定休日
             WHEN d.day_of_week = 6 THEN 1 -- 土曜日、所定休日
             ELSE 0 -- 平日
        END AS date_type,
        CASE WHEN day_off THEN 0 -- 休み
             ELSE 1 -- 出勤
        END AS date_status,
        CASE WHEN not day_off THEN d.day_date + wp.start_time END AS clock_in_time,
        CASE WHEN not day_off THEN d.day_date + wp.end_time END AS clock_out_time,
        CASE WHEN not day_off THEN true ELSE false END AS has_lunch_break,
        CASE WHEN not day_off THEN true ELSE false END AS has_break1,
        CASE WHEN not day_off THEN true ELSE false END AS has_break2,
        CASE WHEN not day_off THEN true ELSE false END AS has_break3,
        CASE WHEN not day_off THEN true ELSE false END AS has_break4,
        CASE WHEN not day_off THEN true ELSE false END AS has_break5
    FROM day_info d
    LEFT JOIN work_pattern wp ON wp.id = v_work_pattern_id;

END;
$$;