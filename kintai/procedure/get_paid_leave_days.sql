CREATE OR REPLACE FUNCTION get_paid_leave_days(hire_date DATE, target_date DATE DEFAULT CURRENT_DATE)
RETURNS INTEGER AS $$
DECLARE
    v_reference_date DATE;
    v_years INTEGER;
BEGIN
    -- 未入社の場合
    IF target_date < hire_date THEN
        RETURN 0;
    END IF;

    -- 10月以後は当年度の10月1日を基準日とする、10月以前は前年の10月1日を基準日とする
    v_reference_date := case when extract(month from target_date)::INT >= 10
                            then MAKE_DATE(EXTRACT(YEAR FROM target_date)::INT, 10, 1)
                            else MAKE_DATE(EXTRACT(YEAR FROM target_date)::INT - 1, 10, 1)
                        end;
    
    --年休計算用勤続年数
    v_years := case when extract(month from hire_date)::INT <= 3
                    then EXTRACT(YEAR FROM v_reference_date) - EXTRACT(YEAR FROM hire_date) + 2
                    else EXTRACT(YEAR FROM v_reference_date) - EXTRACT(YEAR FROM hire_date) + 1
                end;

    -- 最初の10月1日未到来（初年度途中の場合：条件3適用）
    -- 例: 2026年4月入社で、2026年5月時点の付与数を調べる場合など
    IF target_date < (
        CASE 
            WHEN EXTRACT(MONTH FROM hire_date) >= 10 THEN MAKE_DATE(EXTRACT(YEAR FROM hire_date)::INT + 1, 10, 1)
            ELSE MAKE_DATE(EXTRACT(YEAR FROM hire_date)::INT, 10, 1)
        END
    ) THEN
        RETURN CASE EXTRACT(MONTH FROM hire_date)
            WHEN 10 THEN 12
            WHEN 11 THEN 11
            WHEN 12 THEN 10
            WHEN  1 THEN 10
            WHEN  2 THEN 10
            WHEN  3 THEN 10
            WHEN  4 THEN 6
            WHEN  5 THEN 5
            WHEN  6 THEN 4
            WHEN  7 THEN 3
            WHEN  8 THEN 2
            WHEN  9 THEN 1
        END;
    END IF;

    -- 3. 勤務年数に応じた付与日数
    RETURN CASE v_years
        WHEN 1 THEN 12
        WHEN 2 THEN 13
        WHEN 3 THEN 15
        WHEN 4 THEN 17
        WHEN 5 THEN 19
        ELSE 20 -- 6年以上
    END;
END;
$$ LANGUAGE plpgsql;

/*
select '2024-09-01'::date, get_paid_leave_days('2024-09-01'::date) union all
select '2024-09-01'::date, get_paid_leave_days('2024-09-01'::date, '2026-10-01'::date) union all
select '2024-10-01'::date, get_paid_leave_days('2024-10-01'::date) union all
select '2024-10-01'::date, get_paid_leave_days('2024-10-01'::date, '2026-10-01'::date) union all
select '2025-03-01'::date, get_paid_leave_days('2025-03-01'::date) union all
select '2025-03-01'::date, get_paid_leave_days('2025-03-01'::date, '2026-10-01'::date) union all
select '2025-04-01'::date, get_paid_leave_days('2025-04-01'::date) union all
select '2025-04-01'::date, get_paid_leave_days('2025-04-01'::date, '2026-10-01'::date) union all
select '2025-09-01'::date, get_paid_leave_days('2025-09-01'::date) union all
select '2025-09-01'::date, get_paid_leave_days('2025-09-01'::date, '2026-10-01'::date) union all
select '2025-10-01'::date, get_paid_leave_days('2025-10-01'::date) union all
select '2025-10-01'::date, get_paid_leave_days('2025-10-01'::date, '2026-10-01'::date) union all
select '2026-03-01'::date, get_paid_leave_days('2026-03-01'::date) union all
select '2026-03-01'::date, get_paid_leave_days('2026-03-01'::date, '2026-10-01'::date) union all
select '2026-04-01'::date, get_paid_leave_days('2026-04-01'::date) union all
select '2026-04-01'::date, get_paid_leave_days('2026-04-01'::date, '2026-10-01'::date);
*/