# Arquitetura do Servidor Oracle ARM

Documento de referência para o setup do servidor pessoal (Oracle ARM — VM.Standard.A1.Flex).

## Visão Geral

```
Internet
    │
    ▼
Cloudflare Edge
    │  Cloudflare Tunnel (outbound da VM — zero portas abertas)
    ▼
cloudflared (container)
    │ → nginx:80
    ▼
nginx-proxy (container global, rede `proxy`)
    │
    ├── stheisaque.com/api/*  →  wedding-api:3000
    ├── avislab.app/*         →  avislab-api:3000
    └── isaquediniz.com/*     →  isaquediniz-api:3000
```

- SSL termina no Cloudflare Edge — Nginx fala HTTP internamente, zero certificado na VM
- Rede `proxy`: compartilhada entre Nginx e todos os backends
- Rede `{projeto}-internal`: isolada entre backend e banco de cada projeto

## Estrutura de Diretórios na VM

```
/home/isaque/projects/
  nginx/
    docker-compose.yml
    nginx.conf
    conf.d/
      wedding.conf        ← um arquivo por projeto
  cloudflared/
    docker-compose.yml
    .env                  ← TUNNEL_TOKEN (não commitar)
  watchtower/
    docker-compose.yml
  wedding/
    docker-compose.yml
    .env                  ← variáveis do app (não commitar)
```

---

## Passo 1 — Rede Compartilhada

Executar uma única vez na VM:

```bash
docker network create proxy
```

---

## Passo 2 — Nginx

`nginx/docker-compose.yml`:
```yaml
services:
  nginx:
    image: nginx:alpine
    container_name: nginx-proxy
    restart: unless-stopped
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./conf.d:/etc/nginx/conf.d:ro
    networks:
      - proxy

networks:
  proxy:
    external: true
```

`nginx/nginx.conf`:
```nginx
worker_processes auto;

events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    proxy_set_header Host              $host;
    proxy_set_header X-Real-IP         $remote_addr;
    proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    include /etc/nginx/conf.d/*.conf;
}
```

`nginx/conf.d/wedding.conf`:
```nginx
server {
    listen 80;
    server_name stheisaque.com www.stheisaque.com;

    location /api/ {
        proxy_pass http://wedding-api:3000/;
    }
}
```

```bash
cd /home/isaque/projects/nginx && docker compose up -d
```

---

## Passo 3 — Cloudflare Tunnel

1. No dashboard: **Cloudflare → Zero Trust → Networks → Tunnels → Create tunnel** → copiar token

2. Configurar ingress rules no dashboard:
```yaml
ingress:
  - hostname: stheisaque.com
    service: http://nginx:80
  - hostname: www.stheisaque.com
    service: http://nginx:80
  - hostname: avislab.app
    service: http://nginx:80
  - service: http_status:404
```

`cloudflared/docker-compose.yml`:
```yaml
services:
  cloudflared:
    image: cloudflare/cloudflared:latest
    container_name: cloudflared
    restart: unless-stopped
    command: tunnel --no-autoupdate run
    env_file: .env
    networks:
      - proxy

networks:
  proxy:
    external: true
```

`cloudflared/.env` (criar manualmente, não commitar):
```
TUNNEL_TOKEN=<token do dashboard>
```

```bash
cd /home/isaque/projects/cloudflared && docker compose up -d
```

---

## Passo 4 — Watchtower

Autenticar no ghcr.io uma vez (gera `~/.docker/config.json`):
```bash
echo $GHCR_TOKEN | docker login ghcr.io -u isaque --password-stdin
```

`watchtower/docker-compose.yml`:
```yaml
services:
  watchtower:
    image: containrrr/watchtower
    container_name: watchtower
    restart: unless-stopped
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - /home/isaque/.docker/config.json:/config.json:ro
    environment:
      WATCHTOWER_POLL_INTERVAL: 300
      WATCHTOWER_LABEL_ENABLE: "true"
      WATCHTOWER_CLEANUP: "true"
      DOCKER_CONFIG: /config.json
```

```bash
cd /home/isaque/projects/watchtower && docker compose up -d
```

---

## Passo 5 — Wedding Project

`wedding/docker-compose.yml`:
```yaml
services:
  api:
    container_name: wedding-api
    image: ghcr.io/isaque/wedding-api:latest
    restart: unless-stopped
    expose:
      - "3000"
    env_file: .env
    networks:
      - proxy
      - internal
    labels:
      - "com.centurylinklabs.watchtower.enable=true"
    depends_on:
      - mongodb

  mongodb:
    container_name: wedding-mongodb
    image: mongo:7
    restart: unless-stopped
    volumes:
      - mongo-data:/data/db
    networks:
      - internal

volumes:
  mongo-data:

networks:
  proxy:
    external: true
  internal:
    name: wedding-internal
    driver: bridge
```

`wedding/.env` (criar manualmente, não commitar):
```
PORT=3000
MONGO_URI=mongodb://wedding-mongodb:27017/wedding
NODE_ENV=production
```

```bash
cd /home/isaque/projects/wedding && docker compose up -d
```

---

## Passo 6 — CI/CD do Wedding Backend

No repositório do backend, criar `.github/workflows/deploy.yml`:
```yaml
name: Build & Push

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Login to ghcr.io
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          push: true
          tags: ghcr.io/isaque/wedding-api:latest
```

Push no `main` → GitHub Actions builda e publica imagem no `ghcr.io` → Watchtower detecta
em até 5 minutos e reinicia `wedding-api` automaticamente.

---

## Acesso Direto para Debug (sem abrir portas)

```bash
# MongoDB Compass
ssh -L 27017:localhost:27017 isaque@<oracle-ip>
# conectar: mongodb://localhost:27017

# API direta (bypass nginx)
ssh -L 3000:localhost:3000 isaque@<oracle-ip>
# curl http://localhost:3000/health
```

---

## Adicionar Novo Projeto

1. Criar `/home/isaque/projects/{nome}/docker-compose.yml` seguindo o template do wedding
2. Criar `/home/isaque/projects/nginx/conf.d/{nome}.conf` com o `server {}` block
3. Adicionar hostname no ingress do Cloudflare Tunnel (dashboard)
4. `cd /home/isaque/projects/nginx && docker compose restart`
5. `cd /home/isaque/projects/{nome} && docker compose up -d`
6. Criar repo no GitHub com `Dockerfile` e `.github/workflows/deploy.yml`

## Convenções

- Container names: `{projeto}-{serviço}` (ex: `wedding-api`, `wedding-mongodb`)
- Redes internas: `{projeto}-internal`
- Portas internas: definidas pela variável `PORT` no `.env` de cada projeto — sem conflito mesmo que múltiplos projetos usem `3000`
- `.env` reais nunca entram no git
