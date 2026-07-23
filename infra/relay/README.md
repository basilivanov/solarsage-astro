# TCP Egress Relay для продакшена

Этот сервис представляет собой TCP egress-relay на базе Nginx stream с `ssl_preread`.

## Зачем нужен

Прод-хост (`astro.vasiliy-ivanov.ru`, IP `157.22.192.242`) имеет ограничение связности:
- `openrouter.ai` блокирует входящие запросы с IP прода (geo-block 403).
- `api.telegram.org` имеет TCP timeout с провайдера прода.

Dev-хост (`45.88.172.246`, Амстердам) имеет прямой нормальный egress к этим сервисам.

## Как это работает

1. Nginx слушаeт порт **8443** на dev-хосте.
2. Проверяет IP клиента (разрешён только IP прода `157.22.192.242`).
3. Считывает SNI из TLS ClientHello (`ssl_preread on`) без терминирования TLS.
4. Проксирует сырой TCP-поток на целевые хосты (`openrouter.ai:443` или `api.telegram.org:443`).
5. Случайные или неразрешённые SNI сбрасываются (направляются на мёртвый IP `127.0.0.1:9`).

TLS терминируется полностью на целевых серверах (OpenRouter / Telegram), поэтому сертификаты валидны, а код приложения не требует изменений.

## Запуск и эксплуатация

Запуск на dev-хосте:
```bash
docker compose -f infra/relay/docker-compose.yml up -d
```

Проверка идёт **с прод-хоста** (с dev-хоста соединение будет отклонено allowlist — это ожидаемо):
```bash
curl -v --resolve openrouter.ai:8443:45.88.172.246 https://openrouter.ai:8443/api/v1/models
```
Ожидаемый ответ — HTTP 401 от настоящего OpenRouter (TLS проходит end-to-end, ключ не нужен для проверки связности).

## Прод-настройка (выполняется архитектором при rollout)

1. В `infra/production/docker-compose.app.yml` у сервиса `api` прописаны `extra_hosts`:
   - `api.telegram.org:45.88.172.246`
   - `openrouter.ai:45.88.172.246`
2. В `/etc/solarsage/app.env` на проде задаётся:
   `OPENROUTER_BASE_URL=https://openrouter.ai:8443/api/v1`
