CREATE OR REPLACE PROCEDURE calculate_working_time(
    IN p_member_id INT,
    IN p_month DATE,
    IN p_login_username VARCHAR(150),
    IN p_time_unit INT DEFAULT 15
)
LANGUAGE plpgsql
AS $$
DECLARE
    c_work_day INT := 0;             -- 平日
    c_scheduled_day_off INT := 1;   -- 所定休日(土曜日、年末年始など)
    c_statutory_day_off INT := 2;   -- 法定休日（日曜日など）
    c_national_holiday INT := 3;    -- 国民の祝日
    c_transfer_holiday INT := 4;    -- 振替休日
BEGIN
    -- 1. Calculate daily attendance for the given member and month
    WITH work_pattern_info as (
        select id, lunch_break_start_time as break_start, lunch_break_end_time as break_end, 1 break_no from work_pattern
        union all
        select id, break1_start_time as break_start, break1_end_time as break_end, 2 break_no from work_pattern
        union all
        select id, break2_start_time as break_start, break2_end_time as break_end, 3 break_no from work_pattern
        union all
        select id, break3_start_time as break_start, break3_end_time as break_end, 4 break_no from work_pattern
        union all
        select id, break4_start_time as break_start, break4_end_time as break_end, 5 break_no from work_pattern
        union all
        select id, break5_start_time as break_start, break5_end_time as break_end, 6 break_no from work_pattern
    ), daily_attendance_data AS (
        SELECT 
            ad.id, ad.monthly_attendance_id, ad.day, ad.date_type, ad.date_status, ad.work_pattern_id,
            -- date_bin(make_interval(mins => p_time_unit), ad.clock_in_time + (make_interval(mins => p_time_unit) - INTERVAL '1 microsecond'), TIMESTAMPTZ '2000-01-01 00:00:00+00') AS clock_in,
            -- date_bin(make_interval(mins => p_time_unit), ad.clock_out_time, TIMESTAMPTZ '2000-01-01 00:00:00+00') AS clock_out,
            date_bin(make_interval(mins => 15), ad.clock_in_time + (make_interval(mins => 15) - INTERVAL '1 microsecond'), TIMESTAMPTZ '2000-01-01 00:00:00+00') AS clock_in,
            date_bin(make_interval(mins => 15), ad.clock_out_time, TIMESTAMPTZ '2000-01-01 00:00:00+00') AS clock_out,
            (ad.day + wp.start_time)::TIMESTAMP AT TIME ZONE 'Asia/Tokyo' AS adjusted_standard_start,
            (ad.day + wp.end_time + CASE WHEN wp.end_time < wp.start_time THEN INTERVAL '1 day' ELSE INTERVAL '0 day' END)::TIMESTAMP AT TIME ZONE 'Asia/Tokyo' AS adjusted_standard_end,
            ad.has_lunch_break, ad.has_break1, ad.has_break2, ad.has_break3, ad.has_break4, ad.has_break5,
            case when ad.date_status IN (0, 2, 3) -- 0:通常勤務、2:午前半休、3:午後半休
                    AND ad.clock_in_time IS NOT NULL 
                    AND ad.clock_out_time IS NOT NULL
            THEN 1 ELSE 0 END AS is_working_day,
            absence_start , absence_end,
            (extract(epoch from wp.standard_work_time::interval) / 60)::int AS legal_standard_work_minutes, wp.half_day_time
        FROM attendance_monthly am
            INNER JOIN attendance_daily ad ON ad.monthly_attendance_id = am.id
            INNER JOIN work_pattern wp ON wp.id = ad.work_pattern_id
        -- WHERE am.member_id = p_member_id
        --   AND DATE_TRUNC('month', am.month) = DATE_TRUNC('month', p_month)
    ), daily_attendance_with_breaks AS (
        select id, monthly_attendance_id, day, date_type, date_status, clock_in, clock_out, is_working_day,
            adjusted_standard_start, adjusted_standard_end, legal_standard_work_minutes, half_day_time,
            (day + absence_start + case when clock_in > (day + absence_start)::TIMESTAMP AT TIME ZONE 'Asia/Tokyo' then INTERVAL '1 day' else INTERVAL '0 day' end)::TIMESTAMP AT TIME ZONE 'Asia/Tokyo' as break_start_datetime,
            absence_start as break_start, absence_end as break_end, 0 as break_no
        from daily_attendance_data
        union all
        select ad.id, ad.monthly_attendance_id, ad.day, ad.date_type, ad.date_status, ad.clock_in, ad.clock_out, ad.is_working_day,
            ad.adjusted_standard_start, ad.adjusted_standard_end, ad.legal_standard_work_minutes, ad.half_day_time,
            (day + break_start + case when clock_in > (day + break_start)::TIMESTAMP AT TIME ZONE 'Asia/Tokyo' then INTERVAL '1 day' else INTERVAL '0 day' end)::TIMESTAMP AT TIME ZONE 'Asia/Tokyo' as break_start_datetime,
            wpi.break_start, wpi.break_end, wpi.break_no
        from daily_attendance_data ad
        inner join work_pattern_info wpi 
            on ad.work_pattern_id = wpi.id
            and ((wpi.break_no = 1 and ad.has_lunch_break) or
                (wpi.break_no = 2 and ad.has_break1) or
                (wpi.break_no = 3 and ad.has_break2) or
                (wpi.break_no = 4 and ad.has_break3) or
                (wpi.break_no = 5 and ad.has_break4) or
                (wpi.break_no = 6 and ad.has_break5))
    ), ordered_daily_attendance AS (
        SELECT ad.*,
            -- Define Night Windows (22:00 - 05:00 next day)
            CASE WHEN ad.clock_out > (ad.day + '22:00:00'::TIME)::TIMESTAMP AT TIME ZONE 'Asia/Tokyo' 
                 THEN GREATEST((ad.day + '22:00:00'::TIME)::TIMESTAMP AT TIME ZONE 'Asia/Tokyo', ad.clock_in) 
                 ELSE NULL END AS night_work_start,
            CASE WHEN ad.clock_out > (ad.day + '22:00:00'::TIME)::TIMESTAMP AT TIME ZONE 'Asia/Tokyo' 
                 THEN LEAST((ad.day + INTERVAL '1 day' + '05:00:00'::TIME)::TIMESTAMP AT TIME ZONE 'Asia/Tokyo', ad.clock_out) 
                 ELSE NULL END AS night_work_end,
            row_number() OVER (PARTITION BY ad.monthly_attendance_id, ad.day ORDER BY ad.break_start_datetime) AS rn,
           case when ad.legal_standard_work_minutes > (EXTRACT(epoch FROM (ad.break_start_datetime - clock_in)) / 60)::int -
            sum(extract(epoch from ad.break_end - ad.break_start) / 60) over(PARTITION BY ad.monthly_attendance_id, ad.day ORDER BY ad.break_start_datetime )
			then 1 else 0 end legal_period_inclusive,
			sum(extract(epoch from ad.break_end - ad.break_start) / 60) over(PARTITION BY ad.monthly_attendance_id, ad.day ORDER BY ad.break_start_datetime ) total_included_minutes
        FROM daily_attendance_with_breaks ad
    ), daily_attendance_with_legal_end AS (
        SELECT ad.*, od.night_work_start, od.night_work_end,
			ad.clock_in + make_interval(mins => ad.legal_standard_work_minutes::int + coalesce(od.total_included_minutes::int, 0)) legal_end_time
        FROM daily_attendance_with_breaks ad
        left join ordered_daily_attendance od
            on ad.id = od.id
            and od.legal_period_inclusive = 1
            and od.rn = (select max(sub.rn) from ordered_daily_attendance sub where sub.id = od.id and sub.legal_period_inclusive = 1)
    ), calculate_work_time AS (
        SELECT ad.*,
            GREATEST(EXTRACT(epoch FROM ad.clock_in - ad.adjusted_standard_start) / 60, 0)::INTEGER AS late_minutes,
            GREATEST(EXTRACT(epoch FROM ad.adjusted_standard_end - ad.clock_out) / 60, 0)::INTEGER AS early_leave_minutes,

            -- Total work time and break time
            GREATEST(EXTRACT(epoch FROM ad.clock_out - ad.clock_in) / 60, 0)::INTEGER AS total_work_minutes,
            sum(calculate_overlapped(ad.clock_in, ad.clock_out, ad.break_start, ad.break_end)) over(PARTITION BY ad.id) AS total_break_minutes,

            -- Total night work time and night break time
            GREATEST(EXTRACT(epoch FROM ad.night_work_end - ad.night_work_start) / 60, 0)::INTEGER AS total_night_work_minutes,
            sum(calculate_overlapped(ad.night_work_start, ad.night_work_end, ad.break_start, ad.break_end)) over(PARTITION BY ad.id) AS total_night_work_break_minutes,

            -- Total overtime time and overtime break time
            GREATEST(EXTRACT(epoch FROM ad.clock_out - ad.legal_end_time) / 60, 0)::INTEGER AS total_overtime_minutes,
            sum(calculate_overlapped(ad.legal_end_time, ad.clock_out, ad.break_start, ad.break_end)) over(PARTITION BY ad.id) AS total_overtime_break_minutes,
             
            -- Total night overtime time and night overtime break time
            GREATEST(EXTRACT(epoch FROM ad.night_work_end - ad.legal_end_time) / 60, 0)::INTEGER AS total_night_work_overtime_minutes,
            sum(calculate_overlapped(ad.legal_end_time, ad.night_work_end, ad.break_start, ad.break_end)) over(PARTITION BY ad.id) AS total_night_work_overtime_break_minutes
        FROM daily_attendance_with_legal_end ad
    ), calculate_overtime AS (
        select id, monthly_attendance_id, day, date_type, date_status, clock_in, clock_out, is_working_day,
            ad.late_minutes AS late_minutes,
            ad.early_leave_minutes AS early_leave_minutes,
            GREATEST(ad.total_work_minutes - ad.total_break_minutes, 0) AS total_work_minutes,
            GREATEST(ad.total_overtime_minutes - ad.total_overtime_break_minutes, 0) AS total_overtime_minutes,
            GREATEST(ad.total_night_work_overtime_minutes - ad.total_night_work_overtime_break_minutes, 0) AS total_night_work_overtime_minutes,
            GREATEST(ad.total_night_work_minutes - ad.total_night_work_break_minutes - (ad.total_night_work_overtime_minutes - ad.total_night_work_overtime_break_minutes), 0) AS total_night_work_minutes
        FROM calculate_work_time ad
        where ad.break_no = 0
    )
    UPDATE attendance_daily ad
    SET actual_work_minutes = c.total_work_minutes,
        late_minutes = c.late_minutes,
        early_leave_minutes = c.early_leave_minutes,
        overtime_125 = CASE WHEN c.date_type = c_work_day THEN c.total_overtime_minutes - c.total_night_work_overtime_minutes ELSE 0 END,
        overtime_150 = CASE WHEN c.date_type = c_work_day THEN c.total_night_work_overtime_minutes ELSE 0 END,
        night_time_025 = CASE WHEN c.date_type = c_work_day THEN c.total_night_work_minutes ELSE 0 END,
        off_day_125 = CASE WHEN c.date_type = c_scheduled_day_off THEN c.total_work_minutes ELSE 0 END,
        off_day_150 = CASE WHEN c.date_type = c_scheduled_day_off THEN c.total_night_work_overtime_minutes + c.total_night_work_minutes ELSE 0 END,
        holiday_135 = CASE WHEN c.date_type IN (c_statutory_day_off, c_national_holiday, c_transfer_holiday) THEN c.total_work_minutes ELSE 0 END,
        holiday_160 = CASE WHEN c.date_type IN (c_statutory_day_off, c_national_holiday, c_transfer_holiday) THEN c.total_night_work_overtime_minutes + c.total_night_work_minutes ELSE 0 END
    FROM calculate_overtime c
    WHERE ad.id = c.id;

    -- 2. Aggregate monthly attendance for the given member and month
    WITH monthly_attendance_data AS (
        SELECT 
            am.member_id, 
            DATE_TRUNC('month', ad.day) AS month,
            SUM(ad.actual_work_minutes) AS total_actual_work_minutes,
            SUM(CASE ad.date_status WHEN 0 THEN 1 WHEN 2 THEN 0.5 WHEN 3 THEN 0.5 ELSE 0 END) AS total_worked_days,
            SUM(CASE WHEN ad.date_status NOT IN (0,1,2,3) THEN 1 ELSE 0 END) AS total_paid_leave_days,
            SUM(CASE WHEN ad.date_type = c_work_day THEN 1 ELSE 0 END) AS total_standard_working_days,
            SUM(CASE WHEN ad.date_status = 1 THEN 1 ELSE 0 END) AS total_absence_days,
            SUM(CASE WHEN ad.early_leave_minutes > 0 THEN 1 ELSE 0 END) AS total_early_leave_days,
            SUM(CASE WHEN ad.late_minutes > 0 THEN 1 ELSE 0 END) AS total_late_days,
            SUM(ad.overtime_125) AS total_overtime_125,
            SUM(ad.overtime_150) AS total_overtime_150,
            SUM(ad.night_time_025) AS total_night_time_025,
            SUM(ad.off_day_125) AS total_off_day_125,
            SUM(ad.off_day_150) AS total_off_day_150,
            SUM(ad.holiday_135) AS total_holiday_135,
            SUM(ad.holiday_160) AS total_holiday_160
        FROM attendance_monthly am
        INNER JOIN attendance_daily ad ON ad.monthly_attendance_id = am.id
        WHERE am.member_id = p_member_id
          AND DATE_TRUNC('month', am.month) = DATE_TRUNC('month', p_month)
        GROUP BY member_id, DATE_TRUNC('month', day)
    )
    UPDATE attendance_monthly am
    SET actual_work_minutes = m.total_actual_work_minutes,
        worked_days = m.total_worked_days,
        paid_leave_days = m.total_paid_leave_days,
        standard_working_days = m.total_standard_working_days,
        absence_days = m.total_absence_days,
        early_leave_days = m.total_early_leave_days,
        late_days = m.total_late_days,
        overtime_125 = m.total_overtime_125,
        overtime_150 = m.total_overtime_150,
        night_time_025 = m.total_night_time_025,
        off_day_125 = m.total_off_day_125,
        off_day_150 = m.total_off_day_150,
        holiday_135 = m.total_holiday_135,
        holiday_160 = m.total_holiday_160,
        updated_at = NOW(),
        updated_by = p_login_username
    FROM monthly_attendance_data m
    WHERE am.member_id = m.member_id 
      AND am.month = m.month;

END;
$$;