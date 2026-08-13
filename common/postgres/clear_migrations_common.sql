delete from django_migrations where app='common';

drop table tmp_postcode_import;
drop table postcode;
drop table municipality cascade;
drop table prefecture cascade;
drop table holiday;

drop table member cascade;
drop table organization cascade;
drop table work_pattern cascade;
