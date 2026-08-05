@echo off
pushd "%~dp0"
echo Starting Podman containers...

if not exist "pgadmin-data" (
    mkdir pgadmin-data
)

podman compose -f docker-compose.yml up -d
if errorlevel 1 (
    echo "podman compose" failed. Trying "podman-compose"...
    podman-compose -f docker-compose.yml up -d
)
if errorlevel 1 (
    echo "podman-compose" failed. Please ensure you have podman and a compose provider installed.
    popd
    pause
    exit /b 1
)
echo Containers started.
popd
pause
