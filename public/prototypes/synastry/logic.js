const contextNames = { overall: 'общему баллу', love: 'близости', home: 'быту', work: 'делам', travel: 'поездкам' };
const contextLabels = { overall: 'Общая динамика', love: 'Близость', home: 'Быт', work: 'Дела', travel: 'Поездки' };
let selectedContext = 'overall';
let selectedCandidate = 'maxim';
let selectedDetailTab = 'overall';
let toastTimer;

function getStatus(score) {
  if (score >= 87) return ['Очень легко', 'easy', 'быть собой рядом'];
  if (score >= 78) return ['Сильное совпадение', 'chemistry', 'много естественного отклика'];
  if (score >= 68) return ['Есть потенциал', 'potential', 'важны договорённости'];
  return ['Нужна настройка', 'tune', 'лучше не жить на догадках'];
}

function renderCandidates() {
  const list = document.getElementById('candidateList');
  const sorted = Object.values(candidates).sort((a,b) => b.scores[selectedContext] - a.scores[selectedContext]);
  list.innerHTML = sorted.map((person, index) => {
    const score = person.scores[selectedContext];
    const status = getStatus(score);
    const m = person.micro[selectedContext];
    return `
      <button class="candidate ${index === 0 ? 'top-match' : ''}" type="button" onclick="openCandidate('${person.id}')">
        <div class="candidate-top">
          <div class="avatar" style="--avatar-bg:${person.colors[0]};--avatar-ink:${person.colors[1]}">
            ${person.initial}${index === 0 ? '<span class="tiny-star">✦</span>' : ''}
          </div>
          <div>
            <div class="candidate-name">${person.name}</div>
            <div class="candidate-meta">${person.relation}</div>
          </div>
          <div class="candidate-score"><strong>${score}</strong><span>из 100</span></div>
        </div>
        <span class="status ${status[1]}">● ${status[0]}</span>
        <div class="candidate-copy">
          <div class="micro"><b>Получается</b>${m[0]}</div>
          <div class="micro"><b>Учесть</b>${m[1]}</div>
        </div>
        <div class="precision-note">
          <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>
          ${person.precision}
        </div>
      </button>`;
  }).join('');
  document.getElementById('sortLabel').textContent = 'по ' + contextNames[selectedContext];
}

document.querySelectorAll('.chip').forEach(chip => chip.addEventListener('click', () => {
  document.querySelectorAll('.chip').forEach(x => x.classList.remove('active'));
  chip.classList.add('active');
  selectedContext = chip.dataset.context;
  renderCandidates();
}));

function showList() {
  document.getElementById('detailScreen').classList.remove('active');
  document.getElementById('listScreen').classList.add('active');
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function openCandidate(id, tab = null) {
  selectedCandidate = id;
  selectedDetailTab = tab || (selectedContext === 'overall' ? 'overall' : selectedContext);
  renderDetail();
  document.getElementById('listScreen').classList.remove('active');
  document.getElementById('detailScreen').classList.add('active');
  window.scrollTo({ top: 0 });
}

function renderDetail() {
  const p = candidates[selectedCandidate];
  const score = p.scores[selectedDetailTab];
  const status = getStatus(score);
  const summary = p.summary[selectedDetailTab];
  document.getElementById('detailAvatar').textContent = p.initial;
  document.getElementById('detailAvatar').style.setProperty('--avatar-bg', p.colors[0]);
  document.getElementById('detailAvatar').style.setProperty('--avatar-ink', p.colors[1]);
  document.getElementById('detailRelation').textContent = p.relation === 'Отношения' ? 'Романтические отношения' : p.relation;
  document.getElementById('pairTitle').textContent = 'Ты + ' + p.name;
  document.getElementById('pairDates').textContent = p.dates;
  document.getElementById('detailScore').textContent = score;
  document.getElementById('detailStatus').innerHTML = `${status[0]}<small>${status[2]}</small>`;
  document.getElementById('summaryTitle').textContent = summary[0];
  document.getElementById('summaryText').textContent = summary[1];
  document.getElementById('summaryTags').innerHTML = summary[2].map(x => `<span class="tag">${x}</span>`).join('');
  document.querySelectorAll('#detailTabs .tab').forEach(tab => tab.classList.toggle('active', tab.dataset.tab === selectedDetailTab));
  renderDetailContent(p, selectedDetailTab);
}

document.querySelectorAll('#detailTabs .tab').forEach(tab => tab.addEventListener('click', () => {
  selectedDetailTab = tab.dataset.tab;
  renderDetail();
  document.querySelector('.summary-card').scrollIntoView({ behavior: 'smooth', block: 'start' });
}));

function renderDetailContent(p, tab) {
  const s = p.scores;
  const metricOrder = tab === 'overall'
    ? [['Близость', s.love], ['Быт', s.home], ['Дела', s.work], ['Поездки', s.travel]]
    : [['Лёгкость', s[tab]], ['Диалог', Math.max(52, s[tab] - 4)], ['Темп', Math.min(96, s[tab] + 3)], ['Восстановление', Math.max(48, s[tab] - 9)]];

  const content = scenarioCopy(p.id, tab);
  document.getElementById('detailContent').innerHTML = `
    <section class="metric-card">
      <div class="metric-head"><h3>${contextLabels[tab]}</h3><span>где легче / где тоньше</span></div>
      ${metricOrder.map(([label,value]) => `
        <div class="metric">
          <div class="metric-label">${label}</div>
          <div class="track"><i style="--value:${value}"></i></div>
          <div class="metric-value">${value}</div>
        </div>`).join('')}
    </section>

    <div class="block-title"><span class="bubble">✓</span><h2>Что уже работает</h2></div>
    <div class="story-list">${content.strengths.map((x,i) => storyCard(x, i+1, '')).join('')}</div>

    <div class="block-title"><span class="bubble" style="background:var(--rose);color:var(--rose-ink)">!</span><h2>Где может цеплять</h2></div>
    <div class="story-list">${content.frictions.map((x,i) => storyCard(x, i+1, 'warning')).join('')}</div>

    <div class="block-title"><span class="bubble" style="background:var(--sage);color:var(--sage-ink)">→</span><h2>Что помогает паре</h2></div>
    <div class="story-list">${content.repairs.map((x,i) => storyCard(x, i+1, 'solution')).join('')}</div>

    <section class="feedback">
      <h2>Похоже на вас?</h2>
      <p>Твоя обратная связь помогает делать следующие разборы точнее и человечнее.</p>
      <div class="feedback-row">
        <button class="feedback-btn" type="button" onclick="sendFeedback(this, 'Да, очень')">Да, очень</button>
        <button class="feedback-btn" type="button" onclick="sendFeedback(this, 'Частично')">Частично</button>
        <button class="feedback-btn" type="button" onclick="sendFeedback(this, 'Не похоже')">Не похоже</button>
      </div>
      <div class="feedback-thanks" id="feedbackThanks">Сохранили. Спасибо ✦</div>
    </section>

    <details class="method">
      <summary>Как получился этот разбор</summary>
      <p>Мы сопоставляем карту пары и переводим десятки связей в наблюдаемые сценарии: способ сближаться, спорить, делить пространство, принимать решения и восстанавливаться. Балл показывает относительную лёгкость в выбранной сфере, а не гарантирует исход отношений.</p>
    </details>`;
}

function storyCard(item, index, className) {
  return `<article class="story ${className}"><span class="story-index">${index}</span><h3>${item[0]}</h3><p>${item[1]}</p></article>`;
}

function sendFeedback(button, value) {
  button.parentElement.querySelectorAll('.feedback-btn').forEach(x => x.classList.remove('selected'));
  button.classList.add('selected');
  document.getElementById('feedbackThanks').classList.add('show');
  showToast('Ответ «' + value + '» сохранён для этого сравнения');
}

function openAddPerson() {
  document.getElementById('addModal').classList.add('open');
  document.body.style.overflow = 'hidden';
  setTimeout(() => document.getElementById('personName').focus(), 180);
}
function closeAddPerson() {
  document.getElementById('addModal').classList.remove('open');
  document.body.style.overflow = '';
}
function backdropClose(event) { if (event.target.id === 'addModal') closeAddPerson(); }

document.querySelectorAll('.relation').forEach(button => button.addEventListener('click', () => {
  document.querySelectorAll('.relation').forEach(x => x.classList.remove('active'));
  button.classList.add('active');
}));

function toggleUnknownTime() {
  const control = document.getElementById('unknownTime');
  const on = control.classList.toggle('on');
  control.setAttribute('aria-checked', String(on));
  const time = document.getElementById('birthTime');
  time.disabled = on;
  time.style.opacity = on ? '.45' : '1';
}

function generateComparison() {
  const name = document.getElementById('personName').value.trim() || 'Алексей';
  document.getElementById('personForm').classList.add('hide');
  document.getElementById('loaderState').classList.add('show');
  const copies = ['Смотрим, где вы усиливаете друг друга', 'Переводим связи карты в жизненные ситуации', 'Собираем короткий и понятный отчёт'];
  let i = 0;
  const interval = setInterval(() => {
    i = (i + 1) % copies.length;
    document.getElementById('loaderCopy').textContent = copies[i];
  }, 650);
  setTimeout(() => {
    clearInterval(interval);
    candidates.alexey = {
      id: 'alexey', name, initial: name[0].toUpperCase(), relation: document.querySelector('.relation.active').textContent,
      dates: '14 мая 1981 · 17 февраля 1989', colors: ['#dfe8ef', '#4f697e'],
      precision: document.getElementById('unknownTime').classList.contains('on') ? 'Время рождения неизвестно · балл примерный' : 'Точное время рождения',
      scores: { overall: 77, love: 81, home: 68, work: 79, travel: 74 },
      micro: {
        overall: ['Много взаимного интереса', 'Нужно согласовать темп'], love: ['Тёплый отклик', 'Не проверять чувства молчанием'],
        home: ['Умеете дать свободу', 'Разные бытовые приоритеты'], work: ['Хорошо развиваете идеи', 'Нужен один владелец решения'], travel: ['Легко пробуете новое', 'Не перегружать маршрут']
      },
      summary: {
        overall: ['Связь быстро становится значимой', 'Между вами достаточно интереса, чтобы двигаться навстречу, и достаточно различий, чтобы не заскучать. Главная настройка — прямо говорить о темпе и ожиданиях.', ['Интерес', 'Развитие', 'Диалог']],
        love: ['Тепло включается быстро', 'Вы хорошо отвечаете на проявленный интерес, но можете по-разному понимать паузу. Чем меньше проверок и догадок, тем легче раскрывается близость.', ['Тепло', 'Отклик', 'Прямота']],
        home: ['Быт потребует простых правил', 'Свобода важна обоим, но ежедневные приоритеты различаются. Договорённости лучше делать видимыми, а не считать “и так понятными”.', ['Свобода', 'Роли', 'Ритм']],
        work: ['Хорошо придумывать и развивать', 'Вы быстро подхватываете идеи друг друга. Для результата понадобится фиксировать решения и не менять роли посреди процесса.', ['Идеи', 'Рост', 'Фокус']],
        travel: ['Хороший баланс нового и опоры', 'Вы охотно исследуете новое, если хотя бы базовые вещи решены заранее. Тогда поездка не превращается в спор о мелочах.', ['Новое', 'Баланс', 'Гибкость']]
      }
    };
    closeAddPerson();
    document.getElementById('personForm').classList.remove('hide');
    document.getElementById('loaderState').classList.remove('show');
    renderCandidates();
    openCandidate('alexey');
    showToast('Новое сравнение готово');
  }, 2200);
}

function showToast(message) {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 2300);
}

document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && document.getElementById('addModal').classList.contains('open')) closeAddPerson();
});

renderCandidates();
