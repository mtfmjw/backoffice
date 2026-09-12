set CLUSTER=ldjp-kintai
set TASK=ldjp-kintai
set SUBNET=subnet-0c6cde0e9fadd5d8b,subnet-0de7d4da99c2917d2
set SECURITY_GROUP=sg-0bbdd49e547fc6870
set CONTAINER_NAME=Main

aws ecs run-task --region ap-northeast-1 ^
  --cluster %CLUSTER% ^
  --task-definition %TASK% ^
  --launch-type FARGATE ^
  --network-configuration "awsvpcConfiguration={subnets=[%SUBNET%],securityGroups=[%SECURITY_GROUP%],assignPublicIp=ENABLED}" ^
  --overrides containerOverrides=[{name=%CONTAINER_NAME%,command=[python,manage.py,createsuperuser,--noinput],environment=[{name=DJANGO_SUPERUSER_USERNAME,value=admin},{name=DJANGO_SUPERUSER_EMAIL,value=admin@leadingsoft.co.jp},{name=DJANGO_SUPERUSER_PASSWORD,value=P09olp09ol}]}]