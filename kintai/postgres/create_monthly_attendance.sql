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
            CASE 
                WHEN EXTRACT(ISODOW FROM d.day_date) IN (6, 7) OR h.date IS NOT NULL 
                THEN TRUE 
                ELSE FALSE 
            END AS is_holiday
        FROM days d
        LEFT JOIN holiday h ON h.date = d.day_date
    )
    INSERT INTO attendance_daily (
        date, 
        monthly_attendance_id, 
        work_pattern_id, 
        date_type, 
        clock_in_time, 
        clock_out_time
    )
    SELECT 
        d.day_date, 
        p_attendance_id, 
        v_work_pattern_id,
        CASE WHEN d.is_holiday THEN 6 ELSE 0 END AS date_type,
        CASE WHEN NOT d.is_holiday THEN d.day_date + wp.start_time END AS clock_in_time,
        CASE WHEN NOT d.is_holiday THEN d.day_date + wp.end_time END AS clock_out_time
    FROM day_info d
    LEFT JOIN work_pattern wp ON wp.id = v_work_pattern_id;

END;
$$;