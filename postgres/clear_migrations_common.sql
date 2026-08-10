delete from django_migrations where app='common';

drop table postcode cascade;
drop table municipality cascade;
drop table prefecture cascade;
drop table holiday cascade;

drop table member cascade;
drop table organization cascade;
drop table work_pattern cascade;
