delete from django_migrations where app='common';

drop table if EXISTS tmp_postcode_import;
drop table if EXISTS postcode;
drop table if EXISTS municipality cascade;
drop table if EXISTS prefecture cascade;
drop table if EXISTS holiday;

drop table if EXISTS member cascade;
drop table if EXISTS organization cascade;
drop table if EXISTS work_pattern cascade;

drop table if EXISTS transportation_station cascade;
drop table if EXISTS transportation_line cascade;
drop table if EXISTS transportation_company cascade;