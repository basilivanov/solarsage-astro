// AI_HEADER
// module: M-TEST-ONBOARDING-REDUCER
// purpose: Unit tests for onboarding reducer state machine

import { describe, it, expect } from 'vitest';
import {
  onboardingReducer,
  initialOnboardingState,
  isStepValid,
  isValidBirthDate,
  isValidBirthTime,
  selectEffectiveCurrentCity,
  selectEffectiveBirthdayCity,
  selectProgress,
  selectIsFirstStep,
  selectIsLastStep,
  type OnboardingState,
} from '../../lib/reducers/onboarding-reducer';

describe('onboardingReducer', () => {
  it('should start at welcome step', () => {
    expect(initialOnboardingState.step).toBe('welcome');
  });

  it('should advance from welcome to birth', () => {
    const next = onboardingReducer(initialOnboardingState, { type: 'next' });
    expect(next.step).toBe('birth');
  });

  it('should not advance beyond done', () => {
    let state: OnboardingState = { ...initialOnboardingState, step: 'done' };
    state = onboardingReducer(state, { type: 'next' });
    expect(state.step).toBe('done');
  });

  it('should go back from birth to welcome', () => {
    let state = onboardingReducer(initialOnboardingState, { type: 'next' });
    state = onboardingReducer(state, { type: 'back' });
    expect(state.step).toBe('welcome');
  });

  it('should not go back from welcome', () => {
    const state = onboardingReducer(initialOnboardingState, { type: 'back' });
    expect(state.step).toBe('welcome');
  });

  it('should skip to done', () => {
    const state = onboardingReducer(initialOnboardingState, { type: 'skip' });
    expect(state.step).toBe('done');
  });

  it('should reset to initial state', () => {
    let state = onboardingReducer(initialOnboardingState, { type: 'next' });
    state = onboardingReducer(state, { type: 'next' });
    state = onboardingReducer(state, { type: 'reset' });
    expect(state).toEqual(initialOnboardingState);
  });

  it('should set birth date', () => {
    const state = onboardingReducer(initialOnboardingState, {
      type: 'set_birth_date',
      value: { day: '15', month: '01', year: '1990' },
    });
    expect(state.birthDate).toEqual({ day: '15', month: '01', year: '1990' });
  });

  it('should set birth place', () => {
    const city = { name: 'Москва', country: 'Россия', lat: 55.75, lon: 37.61, timezone: 'Europe/Moscow' };
    const state = onboardingReducer(initialOnboardingState, {
      type: 'set_birth_place',
      value: city,
    });
    expect(state.birthPlace).toEqual(city);
  });
});

describe('isValidBirthDate', () => {
  it('should accept valid date', () => {
    expect(isValidBirthDate({ day: '15', month: '01', year: '1990' })).toBe(true);
  });

  it('should reject empty date', () => {
    expect(isValidBirthDate({ day: '', month: '', year: '' })).toBe(false);
  });

  it('should reject Feb 30', () => {
    expect(isValidBirthDate({ day: '30', month: '02', year: '1990' })).toBe(false);
  });

  it('should reject day > 31', () => {
    expect(isValidBirthDate({ day: '32', month: '01', year: '1990' })).toBe(false);
  });

  it('should reject month > 12', () => {
    expect(isValidBirthDate({ day: '15', month: '13', year: '1990' })).toBe(false);
  });

  it('should reject year < 1900', () => {
    expect(isValidBirthDate({ day: '15', month: '01', year: '1800' })).toBe(false);
  });

  it('should reject future year', () => {
    expect(isValidBirthDate({ day: '15', month: '01', year: '2099' })).toBe(false);
  });
});

describe('isValidBirthTime', () => {
  it('should accept valid time', () => {
    expect(isValidBirthTime({ hours: '12', minutes: '00', unknown: false })).toBe(true);
  });

  it('should accept unknown time', () => {
    expect(isValidBirthTime({ hours: '', minutes: '', unknown: true })).toBe(true);
  });

  it('should reject hours > 23', () => {
    expect(isValidBirthTime({ hours: '25', minutes: '00', unknown: false })).toBe(false);
  });

  it('should reject minutes > 59', () => {
    expect(isValidBirthTime({ hours: '12', minutes: '60', unknown: false })).toBe(false);
  });

  it('should reject empty time when not unknown', () => {
    expect(isValidBirthTime({ hours: '', minutes: '', unknown: false })).toBe(false);
  });
});

describe('isStepValid', () => {
  it('welcome is always valid', () => {
    expect(isStepValid(initialOnboardingState)).toBe(true);
  });

  const birthState: OnboardingState = {
    ...initialOnboardingState,
    step: 'birth',
    birthDate: { day: '15', month: '01', year: '1990' },
    birthTime: { hours: '12', minutes: '00', unknown: false },
  };

  it('birth is valid with date+time', () => {
    expect(isStepValid(birthState)).toBe(true);
  });

  it('birth is invalid without date', () => {
    expect(isStepValid({ ...birthState, birthDate: { day: '', month: '', year: '' } })).toBe(false);
  });

  it('place is valid with birthPlace and sameAsBirth', () => {
    const state: OnboardingState = {
      ...initialOnboardingState,
      step: 'place',
      birthPlace: { name: 'Москва', country: 'Россия', lat: 55.75, lon: 37.61 },
      sameAsBirth: true,
    };
    expect(isStepValid(state)).toBe(true);
  });

  it('place is invalid without birthPlace', () => {
    const state: OnboardingState = { ...initialOnboardingState, step: 'place' };
    expect(isStepValid(state)).toBe(false);
  });

  it('place is valid with sameAsBirth=true (no currentCity needed)', () => {
    const state: OnboardingState = {
      ...initialOnboardingState,
      step: 'place',
      birthPlace: { name: 'Москва', country: 'Россия', lat: 55.75, lon: 37.61 },
      sameAsBirth: true,
    };
    expect(isStepValid(state)).toBe(true);
  });

  it('done is always valid', () => {
    expect(isStepValid({ ...initialOnboardingState, step: 'done' })).toBe(true);
  });
});

describe('selectors', () => {
  const city1 = { name: 'Москва', country: 'Россия', lat: 55.75, lon: 37.61, timezone: 'Europe/Moscow' };
  const city2 = { name: 'Питер', country: 'Россия', lat: 59.93, lon: 30.33, timezone: 'Europe/Moscow' };

  it('effectiveCurrentCity returns birthPlace when sameAsBirth', () => {
    const state: OnboardingState = {
      ...initialOnboardingState,
      birthPlace: city1,
      currentCity: city2,
      sameAsBirth: true,
    };
    expect(selectEffectiveCurrentCity(state)).toEqual(city1);
  });

  it('effectiveCurrentCity returns currentCity when not sameAsBirth', () => {
    const state: OnboardingState = {
      ...initialOnboardingState,
      birthPlace: city1,
      currentCity: city2,
      sameAsBirth: false,
    };
    expect(selectEffectiveCurrentCity(state)).toEqual(city2);
  });

  it('effectiveBirthdayCity inherits from currentCity when sameAsCurrent', () => {
    const state: OnboardingState = {
      ...initialOnboardingState,
      sameAsBirth: true,
      birthPlace: city1,
      birthdaySameAsCurrent: true,
    };
    expect(selectEffectiveBirthdayCity(state)).toEqual(city1);
  });

  it('selectProgress returns 0 at welcome step', () => {
    expect(selectProgress(initialOnboardingState)).toBe(0);
  });

  it('selectProgress returns 100 at done step', () => {
    const state: OnboardingState = { ...initialOnboardingState, step: 'done' };
    expect(selectProgress(state)).toBe(100);
  });

  it('selectProgress returns 50 at place step', () => {
    const state: OnboardingState = { ...initialOnboardingState, step: 'place' };
    expect(selectProgress(state)).toBe(50);
  });

  it('selectIsFirstStep returns true at welcome', () => {
    expect(selectIsFirstStep(initialOnboardingState)).toBe(true);
  });

  it('selectIsFirstStep returns false at birth', () => {
    const state: OnboardingState = { ...initialOnboardingState, step: 'birth' };
    expect(selectIsFirstStep(state)).toBe(false);
  });

  it('selectIsLastStep returns true at done', () => {
    const state: OnboardingState = { ...initialOnboardingState, step: 'done' };
    expect(selectIsLastStep(state)).toBe(true);
  });

  it('selectIsLastStep returns false at place', () => {
    const state: OnboardingState = { ...initialOnboardingState, step: 'place' };
    expect(selectIsLastStep(state)).toBe(false);
  });

  it('birthday step is valid with birthdaySameAsCurrent=true and no birthdayCity', () => {
    const state: OnboardingState = {
      ...initialOnboardingState,
      step: 'birthday',
      birthdaySameAsCurrent: true,
      birthdayCity: null,
    };
    expect(isStepValid(state)).toBe(true);
  });

  it('birthday step is invalid with birthdaySameAsCurrent=false and no birthdayCity', () => {
    const state: OnboardingState = {
      ...initialOnboardingState,
      step: 'birthday',
      birthdaySameAsCurrent: false,
      birthdayCity: null,
    };
    expect(isStepValid(state)).toBe(false);
  });
});
