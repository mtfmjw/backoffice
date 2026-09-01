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
    WITH daily_attendance_data AS (
        SELECT 
            ad.id, 
            ad.day, 
            ad.date_type, 
            ad.date_status, 
            wp.name AS work_pattern_name, 
            wp.half_day_time,
            (EXTRACT(epoch FROM wp.standard_work_time) / 60)::INTEGER AS legal_standard_work_minutes,
            (ad.day + wp.start_time) AT TIME ZONE 'Asia/Tokyo' AS standard_work_start,
            (ad.day + wp.end_time + CASE WHEN wp.end_time < wp.start_time THEN INTERVAL '1 day' ELSE INTERVAL '0 day' END) AT TIME ZONE 'Asia/Tokyo' AS standard_work_end,
            CASE 
                WHEN wp.end_time >= wp.start_time THEN (EXTRACT(epoch FROM wp.end_time - wp.start_time) / 60)::INTEGER 
                ELSE (EXTRACT(epoch FROM (INTERVAL '1 day' + wp.end_time - wp.start_time)) / 60)::INTEGER 
            END AS standard_work_minutes,
            
            -- Rounding Clock In up to p_time_unit
            date_bin(make_interval(mins => p_time_unit), ad.clock_in_time + (make_interval(mins => p_time_unit) - INTERVAL '1 microsecond'), TIMESTAMPTZ '2000-01-01 00:00:00+09:00') AS clock_in,
            -- Rounding Clock Out down to p_time_unit
            date_bin(make_interval(mins => p_time_unit), ad.clock_out_time, TIMESTAMPTZ '2000-01-01 00:00:00+09:00') AS clock_out,
            
            ad.has_lunch_break, ad.has_break1, ad.has_break2, ad.has_break3, ad.has_break4, ad.has_break5,
            wp.lunch_break_start_time, wp.lunch_break_end_time,
            wp.break1_start_time, wp.break1_end_time, wp.break2_start_time, wp.break2_end_time,
            wp.break3_start_time, wp.break3_end_time, wp.break4_start_time, wp.break4_end_time,
            wp.break5_start_time, wp.break5_end_time
        FROM attendance_monthly am
        INNER JOIN attendance_daily ad ON ad.monthly_attendance_id = am.id
        INNER JOIN work_pattern wp ON wp.id = ad.work_pattern_id
        WHERE am.member_id = p_member_id
          AND DATE_TRUNC('month', am.month) = DATE_TRUNC('month', p_month)
          AND ad.date_status IN (0, 2, 3) -- 0:通常勤務、2:午前半休、3:午後半休
          AND ad.clock_in_time IS NOT NULL 
          AND ad.clock_out_time IS NOT NULL
    ), 
    calculate_legal_end_time AS (
        SELECT *,
            case WHEN date_status = 2 THEN coalesce(day + half_day_time AT TIME ZONE 'Asia/Tokyo', standard_work_start + make_interval(mins => (legal_standard_work_minutes/2)::INT)) ELSE standard_work_start END AS adjusted_work_start, -- 午前半休時の勤務開始時間を調整
            case WHEN date_status = 3 THEN coalesce(day + half_day_time AT TIME ZONE 'Asia/Tokyo', standard_work_start + make_interval(mins => (legal_standard_work_minutes/2)::INT)) ELSE standard_work_end END AS adjusted_work_end, -- 午後半休時の勤務終了時間を調整
            clock_in + make_interval(mins => legal_standard_work_minutes
                + calculate_overlapped(standard_work_start, standard_work_end, lunch_break_start_time, lunch_break_end_time)
                + calculate_overlapped(standard_work_start, standard_work_end, break1_start_time, break1_end_time)
                + calculate_overlapped(standard_work_start, standard_work_end, break2_start_time, break2_end_time)
                + calculate_overlapped(standard_work_start, standard_work_end, break3_start_time, break3_end_time)
                + calculate_overlapped(standard_work_start, standard_work_end, break4_start_time, break4_end_time)
                + calculate_overlapped(standard_work_start, standard_work_end, break5_start_time, break5_end_time)
            ) AS legal_end_time,
            
            -- Define Night Windows (22:00 - 05:00 next day)
            CASE WHEN clock_out > (day + TIME '22:00:00') AT TIME ZONE 'Asia/Tokyo' 
                 THEN GREATEST((day + TIME '22:00:00') AT TIME ZONE 'Asia/Tokyo', clock_in) 
                 ELSE NULL END AS night_work_start,
                 
            CASE WHEN clock_out > (day + TIME '22:00:00') AT TIME ZONE 'Asia/Tokyo' 
                 THEN LEAST((day + INTERVAL '1 day' + TIME '05:00:00') AT TIME ZONE 'Asia/Tokyo', clock_out) 
                 ELSE NULL END AS night_work_end
        FROM daily_attendance_data
    ),
    calculate_work_time AS (
        SELECT id, day, date_type, date_status, work_pattern_name, standard_work_start, standard_work_end, clock_in, clock_out,
            legal_standard_work_minutes,
            GREATEST(EXTRACT(epoch FROM clock_in - adjusted_work_start) / 60, 0)::INTEGER AS late_minutes,
            GREATEST(EXTRACT(epoch FROM adjusted_work_end - clock_out) / 60, 0)::INTEGER AS early_leave_minutes,
            GREATEST(EXTRACT(epoch FROM clock_out - clock_in) / 60, 0)::INTEGER AS total_work_minutes,
            
            -- Total breaks within actual shift
            (CASE WHEN has_lunch_break THEN calculate_overlapped(clock_in, clock_out, lunch_break_start_time, lunch_break_end_time) ELSE 0 END
             + CASE WHEN has_break1 THEN calculate_overlapped(clock_in, clock_out, break1_start_time, break1_end_time) ELSE 0 END
             + CASE WHEN has_break2 THEN calculate_overlapped(clock_in, clock_out, break2_start_time, break2_end_time) ELSE 0 END
             + CASE WHEN has_break3 THEN calculate_overlapped(clock_in, clock_out, break3_start_time, break3_end_time) ELSE 0 END
             + CASE WHEN has_break4 THEN calculate_overlapped(clock_in, clock_out, break4_start_time, break4_end_time) ELSE 0 END
             + CASE WHEN has_break5 THEN calculate_overlapped(clock_in, clock_out, break5_start_time, break5_end_time) ELSE 0 END) AS total_break_minutes,
             
            GREATEST(EXTRACT(epoch FROM clock_out - legal_end_time) / 60, 0)::INTEGER AS total_overtime_minutes,
            
            -- Overtime breaks
            (CASE WHEN has_lunch_break THEN calculate_overlapped(legal_end_time, clock_out, lunch_break_start_time, lunch_break_end_time) ELSE 0 END
             + CASE WHEN has_break1 THEN calculate_overlapped(legal_end_time, clock_out, break1_start_time, break1_end_time) ELSE 0 END
             + CASE WHEN has_break2 THEN calculate_overlapped(legal_end_time, clock_out, break2_start_time, break2_end_time) ELSE 0 END
             + CASE WHEN has_break3 THEN calculate_overlapped(legal_end_time, clock_out, break3_start_time, break3_end_time) ELSE 0 END
             + CASE WHEN has_break4 THEN calculate_overlapped(legal_end_time, clock_out, break4_start_time, break4_end_time) ELSE 0 END
             + CASE WHEN has_break5 THEN calculate_overlapped(legal_end_time, clock_out, break5_start_time, break5_end_time) ELSE 0 END) AS total_overtime_break_minutes,
             
            GREATEST(EXTRACT(epoch FROM night_work_end - night_work_start) / 60, 0)::INTEGER AS total_night_work_minutes,
            
            -- Night breaks (FIXED ARGUMENT ORDER HERE)
            (CASE WHEN has_lunch_break THEN calculate_overlapped(night_work_start, night_work_end, lunch_break_start_time, lunch_break_end_time) ELSE 0 END
             + CASE WHEN has_break1 THEN calculate_overlapped(night_work_start, night_work_end, break1_start_time, break1_end_time) ELSE 0 END
             + CASE WHEN has_break2 THEN calculate_overlapped(night_work_start, night_work_end, break2_start_time, break2_end_time) ELSE 0 END
             + CASE WHEN has_break3 THEN calculate_overlapped(night_work_start, night_work_end, break3_start_time, break3_end_time) ELSE 0 END
             + CASE WHEN has_break4 THEN calculate_overlapped(night_work_start, night_work_end, break4_start_time, break4_end_time) ELSE 0 END
             + CASE WHEN has_break5 THEN calculate_overlapped(night_work_start, night_work_end, break5_start_time, break5_end_time) ELSE 0 END) AS total_night_work_break_minutes,
             
            GREATEST(EXTRACT(epoch FROM night_work_end - legal_end_time) / 60, 0)::INTEGER AS total_night_work_overtime_minutes,
            
            -- Night overtime breaks (FIXED ARGUMENT ORDER HERE)
            (CASE WHEN has_lunch_break THEN calculate_overlapped(legal_end_time, night_work_end, lunch_break_start_time, lunch_break_end_time) ELSE 0 END
             + CASE WHEN has_break1 THEN calculate_overlapped(legal_end_time, night_work_end, break1_start_time, break1_end_time) ELSE 0 END
             + CASE WHEN has_break2 THEN calculate_overlapped(legal_end_time, night_work_end, break2_start_time, break2_end_time) ELSE 0 END
             + CASE WHEN has_break3 THEN calculate_overlapped(legal_end_time, night_work_end, break3_start_time, break3_end_time) ELSE 0 END
             + CASE WHEN has_break4 THEN calculate_overlapped(legal_end_time, night_work_end, break4_start_time, break4_end_time) ELSE 0 END
             + CASE WHEN has_break5 THEN calculate_overlapped(legal_end_time, night_work_end, break5_start_time, break5_end_time) ELSE 0 END) AS total_night_work_overtime_break_minutes
        FROM calculate_legal_end_time
    ), 
    calculate_overtime AS (
        SELECT id, day, date_type, date_status, work_pattern_name, standard_work_start, standard_work_end, clock_in, clock_out,
            late_minutes,
            early_leave_minutes,
            total_work_minutes - total_break_minutes AS total_work_minutes,
            total_overtime_minutes - total_overtime_break_minutes AS total_overtime_minutes,
            total_night_work_overtime_minutes - total_night_work_overtime_break_minutes AS total_night_work_overtime_minutes,
            total_night_work_minutes - total_night_work_break_minutes - (total_night_work_overtime_minutes - total_night_work_overtime_break_minutes) AS total_night_work_minutes
        FROM calculate_work_time
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
            SUM(ad.early_leave_minutes) + SUM(ad.late_minutes) AS total_absence_minutes,
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
        total_absence_minutes = m.total_absence_minutes,
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