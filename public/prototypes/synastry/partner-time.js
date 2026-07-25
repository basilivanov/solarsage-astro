(() => {
  const modal = document.getElementById('addModal');
  if (!modal) return;

  const fields = [...modal.querySelectorAll('.field')];
  const birthField = fields.find(field => field.querySelector('label')?.textContent.includes('Дата и время рождения'));
  if (!birthField) return;

  const dateInput = birthField.querySelector('input[type="date"]');
  const timeInput = birthField.querySelector('input[type="time"]');
  if (!dateInput || !timeInput) return;

  dateInput.id = 'partnerBirthDate';
  timeInput.id = 'partnerBirthTime';
  let rememberedTime = timeInput.value || '12:00';

  const accuracyRow = document.createElement('div');
  accuracyRow.className = 'time-accuracy-row';
  accuracyRow.innerHTML = `
    <div class="time-accuracy-copy">
      <strong>Точное время неизвестно</strong>
      <span>Можно построить синастрию и без него</span>
    </div>
    <button class="time-switch" id="unknownPartnerTime" type="button" role="switch" aria-checked="false" aria-label="Точное время рождения партнёра неизвестно"></button>`;

  const warning = document.createElement('div');
  warning.className = 'time-warning';
  warning.id = 'partnerTimeWarning';
  warning.innerHTML = `<strong>Расчёт будет частичным</strong>Планеты и основные аспекты останутся. Не показываем ASC и дома партнёра; положение Луны и общий балл помечаем как менее точные.`;

  const precision = document.createElement('div');
  precision.className = 'precision-preview';
  precision.id = 'partnerPrecisionPreview';
  precision.innerHTML = '<i></i><span>Точный расчёт: аспекты, ASC и наложение домов</span>';

  birthField.append(accuracyRow, warning, precision);

  function setUnknownTime(enabled) {
    const switchButton = document.getElementById('unknownPartnerTime');
    switchButton.classList.toggle('on', enabled);
    switchButton.setAttribute('aria-checked', String(enabled));
    warning.classList.toggle('show', enabled);
    timeInput.disabled = enabled;
    timeInput.classList.toggle('time-input-disabled', enabled);

    if (enabled) {
      rememberedTime = timeInput.value || rememberedTime;
      timeInput.value = '';
      timeInput.setAttribute('aria-label', 'Время рождения неизвестно');
      precision.classList.add('approx');
      precision.innerHTML = '<i></i><span>Примерный расчёт: без ASC и домов партнёра</span>';
    } else {
      timeInput.value = rememberedTime;
      timeInput.setAttribute('aria-label', 'Точное время рождения партнёра');
      precision.classList.remove('approx');
      precision.innerHTML = '<i></i><span>Точный расчёт: аспекты, ASC и наложение домов</span>';
    }
  }

  document.getElementById('unknownPartnerTime').addEventListener('click', event => {
    const enabled = event.currentTarget.getAttribute('aria-checked') !== 'true';
    setUnknownTime(enabled);
  });

  const originalFakeGenerate = window.fakeGenerate;
  window.fakeGenerate = function fakeGenerateWithPrecision() {
    const name = document.getElementById('newName')?.value.trim() || 'Алексей';
    const unknown = document.getElementById('unknownPartnerTime')?.getAttribute('aria-checked') === 'true';
    closeModal();
    toast(unknown
      ? `Для ${name}: построим примерную синастрию без домов и ASC`
      : `Для ${name}: построим полную синастрию по точному времени`);
  };

  modal.addEventListener('transitionend', () => {
    if (!modal.classList.contains('open') && typeof originalFakeGenerate === 'function') {
      // Keep the prototype state; no reset so users can reopen and inspect their choice.
    }
  });
})();