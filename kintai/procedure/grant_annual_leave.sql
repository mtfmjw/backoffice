CREATE OR REPLACE PROCEDURE grant_annual_leave(IN grant_year INT, login_user VARCHAR(255)) AS $$
DECLARE 
    v_valid_from DATE;
    v_valid_till DATE;
BEGIN
    v_valid_from := make_date(grant_year, 10, 1);
    v_valid_till := v_valid_from + INTERVAL '2 years' - INTERVAL '1 day';

    WITH member_info AS (
        SELECT 
            id AS member_id,
            get_paid_leave_days(join_date, v_valid_from) AS acquired_days
        FROM member
        WHERE valid_flag = TRUE
    )
    INSERT INTO paid_leave (
        member_id,
        valid_from,
        valid_till,
        acquired_days,
        remaining_days,
        valid_flag,
        created_by,
        created_at,
        updated_by,
        updated_at,
        version
    )
    SELECT 
        member_id,
        v_valid_from AS valid_from,
        v_valid_till AS valid_till,
        acquired_days,
        acquired_days AS remaining_days,
        TRUE AS valid_flag,
        login_user AS created_by,
        NOW() AS created_at,
        login_user AS updated_by,
        NOW() AS updated_at,
        0 AS version
    FROM member_info;
END;
$$ LANGUAGE plpgsql;