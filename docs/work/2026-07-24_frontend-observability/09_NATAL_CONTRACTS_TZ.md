# Slice 09 — natal response contract wiring

## Цель

Добавить diagnostic schemas в четыре уже instrumented natal endpoints без
изменения discriminated-result/error behavior.

## Разрешённые файлы

- `lib/api/natal.ts`
- новый `__tests__/api/natal-instrumentation.test.ts`

Существующий `__tests__/api/natal-report.test.ts` не редактировать.

## Требования

1. Response contracts:
   - preview -> `NatalPreviewReadSchema.safeParse`;
   - generate -> `NatalGenerateResponseSchema.safeParse`;
   - report -> `NatalReportReadSchema.safeParse`;
   - section -> `NatalReportSectionReadSchema.safeParse`.
2. Стабильные contract names/version `v1`, safe/capped issue paths без values и
   сообщений.
3. Сохранить authoritative `.parse`, status mappings 409/501/502/401/404,
   Zod-vs-network catch mapping, exact request bodies и public result unions.
4. Все route templates остаются structural; reportId/sectionId не логируются.
5. Обновить GRACE module contract/map и четыре function blocks с реальными
   delegated events. Не менять UI/payment/access.

## Test

Новый GRACE test mock-ает instrumentedFetch и проверяет:

- четыре operations/routes/contracts;
- validators принимают `natalPreviewPayload`, valid generate,
  `natalReportGeneratingPayload`, valid section и отвергают `{}`;
- generate сохраняет exact `{ forceRegenerate }` POST body;
- report/section actual URL содержит IDs, template — placeholders;
- regression одного status mapping (например report 404) остаётся прежним;
- cleanup mocks/globals.

Проверка:

```bash
npx vitest run __tests__/api/natal-instrumentation.test.ts __tests__/api/natal-report.test.ts && npx tsc --noEmit
```

Другие файлы не менять. Ничего не коммить и не пушить — коммит делает ревьюер.
