# Manual Testing Checklist — Telegram Web App

## Pre-requisites
- [ ] Backend running: `sudo systemctl status solarsage-api` → should show "active (running)"
- [ ] Frontend running: `sudo systemctl status solarsage-frontend` → should show "active (running)"
- [ ] Telegram Desktop or Mobile app installed
- [ ] @vi_astro_bot accessible
- [ ] Evidence folder created: `mkdir -p /tmp/telegram-webapp-evidence`

---

## PRIORITY 1: CRITICAL PATH (Must Pass for Production)

### Test 1: Real Telegram Auth + Complete Onboarding ⭐⭐⭐
**Goal:** New user completes full 5-step onboarding flow

**Pre-test Setup:**
- [ ] Clear browser cache (if testing in browser)
- [ ] Clear localStorage (DevTools → Application → Local Storage → Clear All)
- [ ] Use NEW telegram_id (not previously onboarded)

**Steps:**
1. [ ] Open Telegram Desktop/Mobile
2. [ ] Search for `@vi_astro_bot`
3. [ ] Click "Открыть космос!" button
4. [ ] **Step 1 (Welcome):**
   - [ ] Welcome screen loads (no infinite loading)
   - [ ] Text visible: "астрология" or "личная практика" or similar
   - [ ] Screenshot: `/tmp/telegram-webapp-evidence/01-onboarding-step1-welcome.png`
   - [ ] Click "Далее" (Next) button
5. [ ] **Step 2 (Birth Date/Time):**
   - [ ] Birth date input visible
   - [ ] Birth time input visible
   - [ ] Enter date: `1990-01-15`
   - [ ] Enter time: `14:30`
   - [ ] Screenshot: `/tmp/telegram-webapp-evidence/02-onboarding-step2-birth.png`
   - [ ] Click "Далее" button
6. [ ] **Step 3 (Birth Place):**
   - [ ] City selection visible
   - [ ] Select city: `Moscow` (or any city)
   - [ ] Screenshot: `/tmp/telegram-webapp-evidence/03-onboarding-step3-place.png`
   - [ ] Click "Далее" button
7. [ ] **Step 4 (Birthday Confirmation):**
   - [ ] Summary of entered data visible
   - [ ] Data matches what you entered
   - [ ] Screenshot: `/tmp/telegram-webapp-evidence/04-onboarding-step4-confirm.png`
   - [ ] Click "Далее" button
8. [ ] **Step 5 (Done):**
   - [ ] Completion message visible
   - [ ] Screenshot: `/tmp/telegram-webapp-evidence/05-onboarding-step5-done.png`
   - [ ] Click "Начать" (Start) button
9. [ ] **Redirect to /day/today:**
   - [ ] URL is `/day/today` (check address bar)
   - [ ] Content loads (not infinite loading)
   - [ ] Today's date visible
   - [ ] Screenshot: `/tmp/telegram-webapp-evidence/06-onboarding-complete-today.png`
10. [ ] **Verify localStorage:**
    - [ ] Open DevTools (F12) → Application → Local Storage
    - [ ] Find key: `lumen:onboarded`
    - [ ] Value is `1` or `true`
    - [ ] Screenshot: `/tmp/telegram-webapp-evidence/07-onboarding-localstorage.png`
11. [ ] **Check Console (No Errors):**
    - [ ] Open DevTools (F12) → Console tab
    - [ ] No red errors (warnings OK)
    - [ ] Screenshot: `/tmp/telegram-webapp-evidence/08-onboarding-console.png`

**Expected Result:**
- ✅ All 5 steps complete without errors
- ✅ Redirect to /day/today
- ✅ localStorage flag set
- ✅ No console errors

**If Failed:**
- Note which step failed: ___________
- Error message (if any): ___________
- Screenshot saved: ___________

---

### Test 2: Session Persistence ⭐⭐⭐
**Goal:** User closes Telegram → reopens → still logged in

**Pre-test Setup:**
- [ ] Complete Test 1 first (onboarding)

**Steps:**
1. [ ] Close Telegram app **completely** (not just minimize)
2. [ ] Wait 10 seconds
3. [ ] Reopen Telegram
4. [ ] Open @vi_astro_bot
5. [ ] Click "Открыть космос!" button
6. [ ] **Verify redirect to /day/today:**
   - [ ] URL is `/day/today` (NOT `/onboarding`)
   - [ ] Content loads immediately (no auth screen)
   - [ ] Screenshot: `/tmp/telegram-webapp-evidence/09-session-persistence.png`

**Expected Result:**
- ✅ No re-authentication
- ✅ No onboarding screen
- ✅ Direct to /day/today

**If Failed:**
- Redirected to: ___________
- Error message: ___________

---

### Test 3: Existing User Skip Onboarding ⭐⭐⭐
**Goal:** User who completed onboarding skips it on next visit

**Pre-test Setup:**
- [ ] Complete Test 1 first (onboarding)

**Steps:**
1. [ ] Close Web App (click X or back button in Telegram)
2. [ ] Wait 5 seconds
3. [ ] Reopen @vi_astro_bot → "Открыть космос!"
4. [ ] **Verify redirect to /day/today:**
   - [ ] URL is `/day/today` (NOT `/onboarding`)
   - [ ] Screenshot: `/tmp/telegram-webapp-evidence/10-existing-user-skip.png`

**Expected Result:**
- ✅ No onboarding screen
- ✅ Direct to /day/today

**If Failed:**
- Redirected to: ___________

---

### Test 4: Onboarding Validation ⭐⭐
**Goal:** User enters invalid data → sees validation errors

**Pre-test Setup:**
- [ ] Clear localStorage (start as new user)

**Steps:**
1. [ ] Start onboarding (Step 1 → Step 2)
2. [ ] **Step 2 (Empty Date):**
   - [ ] Leave date field empty
   - [ ] Click "Далее" button
   - [ ] Verify error message appears (e.g., "Введите дату рождения")
   - [ ] Screenshot: `/tmp/telegram-webapp-evidence/11-validation-empty-date.png`
3. [ ] **Step 2 (Empty Time):**
   - [ ] Enter date: `1990-01-15`
   - [ ] Leave time field empty
   - [ ] Click "Далее" button
   - [ ] Verify error message appears (e.g., "Введите время рождения")
   - [ ] Screenshot: `/tmp/telegram-webapp-evidence/12-validation-empty-time.png`
4. [ ] **Step 2 (Valid Data):**
   - [ ] Enter date: `1990-01-15`
   - [ ] Enter time: `14:30`
   - [ ] Click "Далее" button
   - [ ] Verify Step 3 loads (no error)
5. [ ] **Step 3 (Empty City):**
   - [ ] Leave city field empty (or don't select)
   - [ ] Click "Далее" button
   - [ ] Verify error message appears
   - [ ] Screenshot: `/tmp/telegram-webapp-evidence/13-validation-empty-city.png`
6. [ ] **Step 3 (Valid City):**
   - [ ] Select city: `Moscow`
   - [ ] Click "Далее" button
   - [ ] Verify Step 4 loads

**Expected Result:**
- ✅ Validation errors shown for empty fields
- ✅ Cannot proceed with invalid data
- ✅ Can correct and continue

**If Failed:**
- No validation error shown: ___________
- Proceeded with empty data: ___________

---

### Test 5: Browser Refresh Mid-Onboarding ⭐
**Goal:** User refreshes page during onboarding → data preserved or lost?

**Pre-test Setup:**
- [ ] Clear localStorage (start as new user)

**Steps:**
1. [ ] Start onboarding
2. [ ] Complete Step 1 → Step 2
3. [ ] Enter birth date: `1990-01-15`
4. [ ] Enter birth time: `14:30`
5. [ ] **Before clicking "Далее":**
   - [ ] Press F5 (refresh page)
6. [ ] **After refresh:**
   - [ ] Check if data is preserved (date/time still filled)
   - [ ] Check if back to Step 1
   - [ ] Screenshot: `/tmp/telegram-webapp-evidence/14-refresh-mid-onboarding.png`

**Expected Result:**
- Document actual behavior (data preserved or lost)
- No crash or infinite loading

**Actual Behavior:**
- Data preserved: YES / NO
- Restarted from Step 1: YES / NO

---

## PRIORITY 2: CORE FEATURES (High Priority)

### Test 6: Cross-Feature Navigation ⭐⭐
**Goal:** User navigates between all main features

**Pre-test Setup:**
- [ ] Complete onboarding (Test 1)

**Steps:**
1. [ ] Start at `/day/today`
2. [ ] **Navigate to Chat:**
   - [ ] Click "Chat" tab/button
   - [ ] Verify URL is `/chat`
   - [ ] Verify chat interface loads
   - [ ] Screenshot: `/tmp/telegram-webapp-evidence/15-nav-chat.png`
3. [ ] **Navigate to Readings:**
   - [ ] Click "Readings" tab/button
   - [ ] Verify URL is `/readings`
   - [ ] Verify readings page loads
   - [ ] Screenshot: `/tmp/telegram-webapp-evidence/16-nav-readings.png`
4. [ ] **Navigate to Calendar:**
   - [ ] Click "Calendar" tab/button
   - [ ] Verify URL is `/calendar`
   - [ ] Verify calendar loads
   - [ ] Screenshot: `/tmp/telegram-webapp-evidence/17-nav-calendar.png`
5. [ ] **Navigate to Profile:**
   - [ ] Click "Profile" tab/button
   - [ ] Verify URL is `/profile`
   - [ ] Verify profile page loads
   - [ ] Screenshot: `/tmp/telegram-webapp-evidence/18-nav-profile.png`
6. [ ] **Navigate back to Today:**
   - [ ] Click "Today" tab/button
   - [ ] Verify URL is `/day/today`
   - [ ] Verify today page loads
   - [ ] Screenshot: `/tmp/telegram-webapp-evidence/19-nav-back-today.png`

**Expected Result:**
- ✅ All pages load without errors
- ✅ No data loss during navigation
- ✅ No infinite loading

**If Failed:**
- Page that failed to load: ___________
- Error message: ___________

---

### Test 7: Chat — Send Message ⭐⭐
**Goal:** User sends message → receives response

**Steps:**
1. [ ] Navigate to `/chat`
2. [ ] Verify chat interface loads
3. [ ] Type message: `Привет!` (Hello!)
4. [ ] Click "Send" button (or press Enter)
5. [ ] Verify message appears in chat history
6. [ ] Wait for response (max 10 seconds)
7. [ ] Verify response appears
8. [ ] Screenshot: `/tmp/telegram-webapp-evidence/20-chat-send-receive.png`

**Expected Result:**
- ✅ Message sent successfully
- ✅ Response received
- ✅ No errors

**If Failed:**
- Message not sent: ___________
- No response: ___________

---

### Test 8: Readings — View Natal Chart ⭐
**Goal:** User views natal chart

**Steps:**
1. [ ] Navigate to `/readings`
2. [ ] Verify readings page loads
3. [ ] Click "Natal Chart" (or equivalent tab/button)
4. [ ] Verify chart loads (image or SVG)
5. [ ] Screenshot: `/tmp/telegram-webapp-evidence/21-readings-natal-chart.png`

**Expected Result:**
- ✅ Chart loads
- ✅ No errors

**If Failed:**
- Chart not visible: ___________

---

### Test 9: Calendar — Navigate Months ⭐
**Goal:** User navigates calendar months → selects date

**Steps:**
1. [ ] Navigate to `/calendar`
2. [ ] Verify current month displayed (e.g., "May 2026")
3. [ ] Click "Previous Month" arrow (←)
4. [ ] Verify previous month loads (e.g., "April 2026")
5. [ ] Screenshot: `/tmp/telegram-webapp-evidence/22-calendar-prev-month.png`
6. [ ] Click "Next Month" arrow (→) twice
7. [ ] Verify next month loads (e.g., "June 2026")
8. [ ] Screenshot: `/tmp/telegram-webapp-evidence/23-calendar-next-month.png`
9. [ ] Click on a date (e.g., 15th)
10. [ ] Verify redirect to `/day/2026-06-15` (or similar)
11. [ ] Screenshot: `/tmp/telegram-webapp-evidence/24-calendar-select-date.png`

**Expected Result:**
- ✅ Month navigation works
- ✅ Date selection navigates to /day/[date]
- ✅ No errors

**If Failed:**
- Navigation not working: ___________

---

### Test 10: Profile — Edit Birth Data ⭐
**Goal:** User edits birth data → saves → data updated

**Steps:**
1. [ ] Navigate to `/profile`
2. [ ] Verify profile page loads
3. [ ] Verify current birth data displayed (from onboarding)
4. [ ] Click "Edit" button (or equivalent)
5. [ ] Change birth date to `1991-02-20`
6. [ ] Change birth time to `10:00`
7. [ ] Screenshot: `/tmp/telegram-webapp-evidence/25-profile-edit.png`
8. [ ] Click "Save" button
9. [ ] Verify success message appears
10. [ ] Refresh page (F5)
11. [ ] Verify new data persisted (shows `1991-02-20` and `10:00`)
12. [ ] Screenshot: `/tmp/telegram-webapp-evidence/26-profile-saved.png`

**Expected Result:**
- ✅ Data saved successfully
- ✅ Persisted after refresh

**If Failed:**
- Data not saved: ___________

---

### Test 11: Day View — Navigate Past/Future ⭐
**Goal:** User navigates to past/future days

**Steps:**
1. [ ] Start at `/day/today`
2. [ ] Note current date (e.g., "May 31, 2026")
3. [ ] Click "Previous Day" arrow (←)
4. [ ] Verify URL is `/day/2026-05-30` (yesterday)
5. [ ] Verify content loads for yesterday
6. [ ] Screenshot: `/tmp/telegram-webapp-evidence/27-day-yesterday.png`
7. [ ] Click "Next Day" arrow (→) twice
8. [ ] Verify URL is `/day/2026-06-01` (tomorrow)
9. [ ] Verify content loads for tomorrow
10. [ ] Screenshot: `/tmp/telegram-webapp-evidence/28-day-tomorrow.png`

**Expected Result:**
- ✅ Navigation works
- ✅ Data loads for each day
- ✅ No errors

**If Failed:**
- Navigation not working: ___________

---

## PRIORITY 3: ERROR SCENARIOS (Medium Priority)

### Test 12: Backend Down ⭐⭐
**Goal:** User opens app when backend is down

**Pre-test Setup:**
- [ ] Stop backend: `sudo systemctl stop solarsage-api`

**Steps:**
1. [ ] Open @vi_astro_bot → "Открыть космос!"
2. [ ] Wait for page to load (max 15 seconds)
3. [ ] **Verify error message:**
   - [ ] Error message visible (NOT infinite loading)
   - [ ] Message mentions "сервер" or "ошибка" or similar
   - [ ] Screenshot: `/tmp/telegram-webapp-evidence/29-error-backend-down.png`
4. [ ] **Restart backend:**
   - [ ] Run: `sudo systemctl start solarsage-api`
   - [ ] Wait 5 seconds
5. [ ] Click "Retry" button (or refresh page)
6. [ ] Verify data loads successfully
7. [ ] Screenshot: `/tmp/telegram-webapp-evidence/30-error-backend-recovered.png`

**Expected Result:**
- ✅ Clear error message (not infinite loading)
- ✅ No crash
- ✅ Recovery after backend restart

**If Failed:**
- Infinite loading: ___________
- No error message: ___________

---

### Test 13: Slow Network (3G Simulation) ⭐
**Goal:** User on slow network

**Pre-test Setup:**
- [ ] Open DevTools (F12) → Network tab
- [ ] Set throttling to "Slow 3G"

**Steps:**
1. [ ] Open @vi_astro_bot → "Открыть космос!"
2. [ ] Verify loading spinner appears
3. [ ] Wait for content to load (max 30 seconds)
4. [ ] Verify content eventually loads
5. [ ] Screenshot: `/tmp/telegram-webapp-evidence/31-slow-network.png`

**Expected Result:**
- ✅ Loading spinner visible
- ✅ Content eventually loads
- ✅ No timeout errors

**If Failed:**
- Timeout error: ___________

---

### Test 14: Session Expired Mid-Session ⭐
**Goal:** User's session expires while using app

**Pre-test Setup:**
- [ ] Complete onboarding (Test 1)

**Steps:**
1. [ ] Open DevTools (F12) → Application → Cookies
2. [ ] Find `session_id` cookie
3. [ ] Delete `session_id` cookie
4. [ ] Navigate to `/chat` (or any page)
5. [ ] **Verify behavior:**
   - [ ] Redirect to auth screen: YES / NO
   - [ ] Error message shown: YES / NO
   - [ ] Screenshot: `/tmp/telegram-webapp-evidence/32-session-expired.png`

**Expected Result:**
- ✅ Graceful handling (no crash)
- ✅ Clear error or re-auth flow

**Actual Behavior:**
- Redirected to: ___________
- Error message: ___________

---

### Test 15: Invalid User Data (Corrupted localStorage) ⭐
**Goal:** User has corrupted localStorage

**Pre-test Setup:**
- [ ] Complete onboarding (Test 1)

**Steps:**
1. [ ] Open DevTools (F12) → Application → Local Storage
2. [ ] Find key: `lumen:onboarded`
3. [ ] Change value to: `invalid_value`
4. [ ] Refresh page (F5)
5. [ ] **Verify behavior:**
   - [ ] Redirect to onboarding: YES / NO
   - [ ] Error message shown: YES / NO
   - [ ] Screenshot: `/tmp/telegram-webapp-evidence/33-corrupted-localstorage.png`

**Expected Result:**
- ✅ Graceful handling (no crash)
- ✅ Redirect to onboarding or error message

**Actual Behavior:**
- Redirected to: ___________
- Error message: ___________

---

## PRIORITY 4: MOBILE-SPECIFIC (Nice to Have)

### Test 16: Touch Gestures (Mobile) ⭐
**Goal:** User swipes between days

**Pre-test Setup:**
- [ ] Open @vi_astro_bot on **mobile device** (iOS or Android)

**Steps:**
1. [ ] Navigate to `/day/today`
2. [ ] Swipe left (to next day)
3. [ ] Verify URL changes to `/day/[tomorrow]`
4. [ ] Swipe right (to previous day)
5. [ ] Verify URL changes to `/day/[yesterday]`

**Expected Result:**
- ✅ Swipe gestures work
- ✅ Smooth navigation

**If Failed:**
- Swipe not working: ___________

---

### Test 17: Keyboard Handling (Mobile) ⭐
**Goal:** User types in chat → keyboard opens → viewport adjusts

**Pre-test Setup:**
- [ ] Open @vi_astro_bot on **mobile device**

**Steps:**
1. [ ] Navigate to `/chat`
2. [ ] Tap on message input field
3. [ ] Verify keyboard opens
4. [ ] Verify input field visible (not hidden by keyboard)
5. [ ] Type message: `Test`
6. [ ] Send message
7. [ ] Verify message sent

**Expected Result:**
- ✅ Keyboard opens
- ✅ Input field visible
- ✅ Message sent

**If Failed:**
- Input hidden by keyboard: ___________

---

## Test Summary

### Results:
- **Total Tests:** 17
- **Passed:** _____ / 17
- **Failed:** _____ / 17
- **Coverage:** _____ %

### Critical Path (Priority 1):
- [ ] Test 1: Real Telegram Auth + Complete Onboarding — PASS / FAIL
- [ ] Test 2: Session Persistence — PASS / FAIL
- [ ] Test 3: Existing User Skip Onboarding — PASS / FAIL
- [ ] Test 4: Onboarding Validation — PASS / FAIL
- [ ] Test 5: Browser Refresh Mid-Onboarding — PASS / FAIL

### Core Features (Priority 2):
- [ ] Test 6: Cross-Feature Navigation — PASS / FAIL
- [ ] Test 7: Chat — Send Message — PASS / FAIL
- [ ] Test 8: Readings — View Natal Chart — PASS / FAIL
- [ ] Test 9: Calendar — Navigate Months — PASS / FAIL
- [ ] Test 10: Profile — Edit Birth Data — PASS / FAIL
- [ ] Test 11: Day View — Navigate Past/Future — PASS / FAIL

### Error Scenarios (Priority 3):
- [ ] Test 12: Backend Down — PASS / FAIL
- [ ] Test 13: Slow Network — PASS / FAIL
- [ ] Test 14: Session Expired Mid-Session — PASS / FAIL
- [ ] Test 15: Invalid User Data — PASS / FAIL

### Mobile-Specific (Priority 4):
- [ ] Test 16: Touch Gestures — PASS / FAIL
- [ ] Test 17: Keyboard Handling — PASS / FAIL

---

## Issues Found

### Issue 1:
- **Test:** ___________
- **Description:** ___________
- **Severity:** Critical / High / Medium / Low
- **Screenshot:** ___________

### Issue 2:
- **Test:** ___________
- **Description:** ___________
- **Severity:** Critical / High / Medium / Low
- **Screenshot:** ___________

### Issue 3:
- **Test:** ___________
- **Description:** ___________
- **Severity:** Critical / High / Medium / Low
- **Screenshot:** ___________

---

## Evidence

All screenshots saved to: `/tmp/telegram-webapp-evidence/`

**Total Screenshots:** _____ files

---

## Sign-off

**Tester:** ___________  
**Date:** ___________  
**Environment:** Production (dev.astro.vasiliy-ivanov.ru)  
**Telegram Client:** Desktop / iOS / Android

**Production Ready:** YES / NO

**Notes:**
___________
___________
___________
