delete from django_migrations where app='kintai';

drop table IF EXISTS attendance_daily cascade;
drop table IF EXISTS attendance_monthly cascade;
