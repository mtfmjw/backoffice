delete from django_migrations where app='kintai';

drop table IF EXISTS attendance_daily cascade;
drop table IF EXISTS attendance_monthly cascade;
drop table IF EXISTS commuting_route_register;
drop table if EXISTS transportation_expense_detail;
drop table IF EXISTS monthly_transportation_expense_report;