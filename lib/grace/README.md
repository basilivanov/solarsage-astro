// AI_HEADER
// module: M-WEB-GRACE-API-README
// wave: W-2.1
// purpose: Documentation for GRACE frontend API layer

# GRACE Frontend API Layer

## Overview

Type-safe API client and React hooks for SolarSage Astro backend endpoints.

## Structure

```
lib/grace/
├── api/
│   └── client.ts       # Fetch functions with error handling
├── hooks/
│   ├── useDay.ts       # React hook for TodayPayload
│   └── useCalendar.ts  # React hook for CalendarPayload
└── index.ts            # Barrel exports
```

## Usage

### API Client

```typescript
import { fetchDay, fetchCalendar, ApiError } from '@/lib/grace';

// Fetch day data
try {
  const dayData = await fetchDay('2026-05-30');
  console.log(dayData.headline);
} catch (error) {
  if (error instanceof ApiError) {
    console.error(`API Error ${error.status}: ${error.message}`);
    if (error.code) {
      console.error(`Error code: ${error.code}`);
    }
  }
}

// Fetch calendar data
const calendarData = await fetchCalendar('2026-05');
```

### React Hooks

```typescript
import { useDay, useCalendar } from '@/lib/grace';

function DayView({ date }: { date: string }) {
  const { data, loading, error } = useDay(date);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;
  if (!data) return null;

  return (
    <div>
      <h1>{data.title}</h1>
      <p>{data.headline}</p>
    </div>
  );
}

function CalendarView({ month }: { month: string }) {
  const { data, loading, error } = useCalendar(month);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;
  if (!data) return null;

  return (
    <div>
      <h2>{data.title}</h2>
      {data.days.map(day => (
        <div key={day.date}>{day.date}</div>
      ))}
    </div>
  );
}
```

## Type Safety

All types are generated from Pydantic schemas via `packages/contracts/_generated.ts`.

```typescript
import type { components } from '@/packages/contracts/_generated';

type TodayPayload = components['schemas']['TodayPayload'];
type CalendarPayload = components['schemas']['CalendarPayload'];
type ContentAccessState = components['schemas']['ContentAccessState'];
```

## Error Handling

The `ApiError` class provides structured error information:

```typescript
class ApiError extends Error {
  status: number;      // HTTP status code
  code?: string;       // Optional error code from backend
  message: string;     // Error message
}
```

## Environment Variables

Set `NEXT_PUBLIC_API_URL` to configure the backend URL:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Default: `http://localhost:8000`

## Testing

Unit tests are in `__tests__/hooks/`:
- `useDay.test.ts` - Tests for useDay hook
- `useCalendar.test.ts` - Tests for useCalendar hook

Run tests:
```bash
pnpm test __tests__/hooks/
```

## GRACE Compliance

- **Wave**: W-2.1 (PHASE-2-FRONTEND-PORT)
- **Module IDs**: M-WEB-API-CLIENT, M-WEB-HOOKS-USE-DAY, M-WEB-HOOKS-USE-CALENDAR
- **Contract Version**: Synced with backend via `packages/contracts/_generated.ts`
- **No UI Changes**: This wave only adds types and data fetching layer
