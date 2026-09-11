podman-compose up --build -d

:: Command Prompt
:: podman-compose up -d --force-recreate nginx
:: podman ps
:: podman-compose restart web

:: Build the Podman container without composing
:: podman build -t django-fargate .
:: podman run -d --name django-fargate -p 0.0.0.0:8000:8000 django-fargate
:: netstat -an | find "8000"

:: OpenSSL command to generate self-signed certificate
:: openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout nginx/certs/privkey.pem -out nginx/certs/fullchain.pem -subj "/CN=localhost" -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"

:: PowerShell
:: New-NetFirewallRule -DisplayName "Podman Nginx Ports" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8080,8443
:: Import-Certificate -FilePath "C:\path\to\your\nginx\certs\fullchain.pem" -CertStoreLocation Cert:\LocalMachine\Root

:: WSL
:: podman exec -it nginx_proxy nginx -t
:: podman logs django_web --tail 50
:: curl -vk https://localhost:8443
