CREATE OR REPLACE FUNCTION calculate_overlapped(
    p_shift_start TIMESTAMPTZ,
    p_shift_end   TIMESTAMPTZ,
    p_win_start   TIME,
    p_win_end     TIME,
    p_timezone    TEXT DEFAULT 'Asia/Tokyo' -- Local timezone where win_start/win_end apply
) 
RETURNS INT 
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    v_start_local TIMESTAMP;
    v_end_local   TIMESTAMP;
    v_total       INT := 0;
BEGIN
    -- Return 0 for invalid or missing inputs
    IF p_shift_start IS NULL OR p_shift_end IS NULL 
       OR p_win_start IS NULL OR p_win_end IS NULL 
       OR p_shift_end <= p_shift_start THEN
        RETURN 0;
    END IF;

    -- Convert timezone-aware timestamps to local TIMESTAMP in target timezone
    v_start_local := p_shift_start AT TIME ZONE p_timezone;
    v_end_local   := p_shift_end AT TIME ZONE p_timezone;

    -- Calculate overlap minutes across each local calendar day
    SELECT COALESCE(
        SUM(
            GREATEST(
                0,
                EXTRACT(EPOCH FROM (
                    LEAST(v_end_local, d.day + p_win_end) 
                    - 
                    GREATEST(v_start_local, d.day + p_win_start)
                )) / 60
            )
        ), 0
    )
    INTO v_total
    FROM generate_series(
        v_start_local::date, 
        v_end_local::date, 
        INTERVAL '1 day'
    ) AS d(day);

    RETURN v_total;
END;
$$;