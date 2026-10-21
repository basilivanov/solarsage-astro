# Публикация отчётов и скриншотов (CF tunnel)

> Часть operative canon репозитория (вместе с AGENTS.md и `docs/agents/*`).
> Извлечено из AGENTS.md 2026-10-22; AGENTS.md содержит резюме и ссылку на этот файл.
> Обращаться сюда, когда владельцу нужно показать артефакты: visual baseline PNG,
> e2e-скриншоты, HTML-отчёты.

Когда владельцу нужно посмотреть артефакты (visual baseline PNG, e2e-скриншоты,
HTML-отчёты) — выкладываем их через **Cloudflare quick tunnel**, а не
скриншотами в чат и не на внешний хостинг.

Канонический способ:

```bash
# 1. собрать витрину (png + index.html с сеткой) во временный каталог
mkdir -p /tmp/artifact-showcase && cp <артефакты> /tmp/artifact-showcase/
# 2. static server на свободном loopback-порту
cd /tmp/artifact-showcase && nohup python3 -m http.server 18923 --bind 127.0.0.1 &
# 3. quick tunnel (без аккаунта; URL живёт, пока жив процесс)
nohup cloudflared tunnel --url http://127.0.0.1:18923 --no-autoupdate > tunnel.log 2>&1 &
# URL: grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" tunnel.log | head -1
```

- `cloudflared` лежит в `/tmp/cloudflared` (linux-amd64 binary из официальных
  GitHub releases; переустановка — скачать заново тем же способом).
- Quick tunnel — временный (до рестарта процесса/хоста). Если нужен
  постоянный URL — named tunnel через аккаунт Cloudflare (отдельное решение
  владельца).
- Выкладываются ТОЛЬКО публично безопасные артефакты: masked visual
  baselines, screenshots, aggregated reports. Никаких логов с user ids,
  env, дампов или fixture'ов с персональными данными.

Активная витрина (приёмка Today Convergence, 2026-08-01 раунд 2: импульсы, drilldown-драйверы, календарь):
`/tmp/baseline-showcase/` (30 PNG + index.html), server :18923,
quick tunnel `https://knee-modes-essential-drivers.trycloudflare.com` (живёт, пока жив процесс).
