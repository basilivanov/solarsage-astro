# apps/solarsage — sidecar расчётов

Отдельный Python-сервис на Swiss Ephemeris. Слушает `127.0.0.1:18091` и
наружу не торчит. Backend ходит к нему через `SOLARSAGE_BASE_URL` +
`X-API-Key: $SOLARSAGE_API_KEY`.

## Содержимое папки

- `collect_solarsage_western_deep.py` — справочный скрипт сбора deep-натала
  (шёл в проекте). Используется как образец payload, который ожидает
  оркестратор.
- `sample_params.json` — пример входных данных.
- `Makefile` — установка sidecar в `/opt/solarsage`, сборка Swiss Ephemeris,
  systemd unit.

## Установка на VDS

```bash
make install   # клонирует SolarSage в /opt/solarsage и собирает libswe.a
make systemd   # ставит /etc/systemd/system/solarsage.service
sudo systemctl enable --now solarsage
```

> SolarSage — внешний репозиторий. Подставь свой URL в `Makefile`
> (`SOLARSAGE_GIT`).

## Проверка

```bash
curl -s -H "X-API-Key: $SOLARSAGE_API_KEY" http://127.0.0.1:18091/health
python collect_solarsage_western_deep.py \
  --name Vasiliy \
  --date 1990-01-01 --time 12:00 --timezone Asia/Yekaterinburg \
  --location Yekaterinburg --lat 56.84 --lon 60.61 \
  --out /tmp/snapshot.json
```
