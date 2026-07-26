(() => {
  const modal = document.createElement('div');
  modal.className = 'modal';
  modal.id = 'aspectModal';
  modal.setAttribute('role', 'dialog');
  modal.setAttribute('aria-modal', 'true');
  modal.setAttribute('aria-labelledby', 'aspectModalTitle');
  modal.innerHTML = `<div class="sheet aspect-sheet">
    <div class="sheet-grab" aria-hidden="true"></div>
    <div class="sheet-head">
      <div><p class="eyebrow">Астрологический контакт</p><h2 id="aspectModalTitle">Что это значит</h2></div>
      <button class="icon-btn" type="button" data-close-aspect aria-label="Закрыть">×</button>
    </div>
    <div id="aspectModalContent"></div>
    <button class="primary full aspect-close" type="button" data-close-aspect>Понятно</button>
  </div>`;
  modal.addEventListener('click', event => {
    if (event.target === modal || event.target.closest('[data-close-aspect]')) closeAspectModal();
  });
  document.body.appendChild(modal);

  const planetMeaning = {
    Солнце: 'ядро личности, воля, чувство «я» и способ проявляться',
    Луна: 'эмоциональные реакции, безопасность, привычки и потребность в заботе',
    Меркурий: 'мышление, речь, логика, вопросы и способ понимать смысл',
    Венера: 'симпатия, нежность, вкус, удовольствие и язык любви',
    Марс: 'действие, желание, напор, сексуальная энергия и способ конфликтовать',
    Юпитер: 'рост, вера, щедрость, смысл и готовность расширять возможности',
    Сатурн: 'границы, ответственность, страх ошибки, правила и устойчивость',
    Уран: 'свобода, внезапность, независимость и потребность менять привычное',
    Нептун: 'идеализация, эмпатия, фантазия, растворение границ и тонкое восприятие',
    Плутон: 'власть, глубина, контроль, ревность, кризис и сильная трансформация',
    ASC: 'первое впечатление, телесная подача и способ входить в контакт'
  };

  const planetGlyph = {
    Солнце: '☉', Луна: '☽', Меркурий: '☿', Венера: '♀', Марс: '♂',
    Юпитер: '♃', Сатурн: '♄', Уран: '♅', Нептун: '♆', Плутон: '♇', ASC: 'AC'
  };

  const aspectMeaning = {
    '☌': { name: 'Соединение', text: 'Две функции сливаются и усиливают друг друга. Контакт ощущается ярко и непосредственно: легко влиять друг на друга, но труднее отделить своё от партнёрского.' },
    '△': { name: 'Тригон', text: 'Энергии поддерживают друг друга естественно. Многое получается без долгой настройки; слабое место — считать эту лёгкость гарантированной.' },
    '✶': { name: 'Секстиль', text: 'Между функциями есть рабочая возможность. Контакт раскрывается, когда пара действительно действует и создаёт совместный опыт.' },
    '□': { name: 'Квадрат', text: 'Два способа действовать сталкиваются под прямым углом. Разницу невозможно долго игнорировать: она даёт раздражение и повторяющиеся сцены, но при ясных правилах может развивать обоих.' },
    '☍': { name: 'Оппозиция', text: 'Партнёры стоят на разных полюсах одной темы. Сначала это притягивает и дополняет, затем может превратиться в качели «либо по-моему, либо по-твоему».' },
    '⚻': { name: 'Квиконс', text: 'Функции будто говорят на несовместимых настройках. Здесь меньше открытого конфликта, но больше странного рассинхрона и постоянной перенастройки.' }
  };

  function escapeAttr(value) {
    return String(value).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  const baseRenderWheel = renderWheel;
  renderWheel = function renderWheelWithDrilldown() {
    baseRenderWheel();
    document.querySelectorAll('.aspect-line').forEach((line, index) => {
      line.onclick = () => openAspectMeaning(index);
    });
  };

  aspectHTML = function aspectHTMLWithDrilldown(a, index) {
    return `<button class="aspect ${a.tone}" data-aspect="${index}" type="button" onclick="openAspectMeaning(${index})">
      <div class="aspect-head"><span class="aspect-symbol">${a.symbol}</span><span class="aspect-tech">${a.a} ${a.kind} ${a.b}</span><span class="orb">орб ${a.orb}</span></div>
      <div class="aspect-human">${a.short}</div>
      <div class="aspect-hint">Нажми — подробное значение и примеры</div>
    </button>`;
  };

  renderTranslations = function renderTranslationsWithDrilldown() {
    document.getElementById('translationGrid').innerHTML = current.translations.map(item => `<div class="translation">
      <div class="translation-top"><i class="tone-dot ${item.tone}"></i><h3>${item.title}</h3><button class="techline" type="button" data-tech="${escapeAttr(item.tech)}" onclick="openAspectFromTech(this.dataset.tech)" title="Открыть подробное значение">${item.tech} · что значит?</button></div>
      <p>${item.text}</p><div class="scene">${item.scene}</div>
    </div>`).join('');
  };

  const baseOpenPerson = openPerson;
  openPerson = function openPersonWithTranslationDrilldown(id) {
    baseOpenPerson(id);
    renderTranslations();
  };

  function mercurySquareDetail() {
    return {
      headline: 'Два разных способа собирать смысл',
      intro: 'Оба Меркурия отвечают за мышление и речь, но квадрат делает сам способ объяснять напряжённым. Один может говорить от вывода, другой — от контекста; один слышит буквальный смысл, другой прежде всего тон и подтекст.',
      scenes: [
        ['В переписке', 'Ты пишешь: «Давай решим это сегодня», имея в виду срочность. Партнёр может услышать приказ или недоверие — и отвечает уже на давление, а не на вопрос.'],
        ['Когда строите планы', 'Один сразу перескакивает к решению, второй хочет сначала разобрать детали. Первому кажется, что разговор тормозят; второму — что его не слушают.'],
        ['В споре', 'Один защищает точную формулировку: «я такого не говорил». Второй защищает пережитый смысл: «но это именно так прозвучало». Оба искренни, но спорят на разных уровнях.'],
        ['После разговора', 'Каждый уверен, что объяснил всё очевидно, и помнит разные ключевые фразы. Поэтому конфликт может повторяться почти дословно — без ощущения, что прошлый разговор что-то изменил.']
      ],
      repairs: [
        'Перед важным разговором назвать цель: «мы сейчас ищем решение или пытаемся понять друг друга?»',
        'После сложной фразы пересказать своими словами: «я услышал, что… Верно?» — без сарказма и суда.',
        'Не решать чувствительные темы короткими сообщениями. Голос и паузы здесь передают половину смысла.',
        'Разбирать один вопрос за раз. Не добавлять к опозданию деньги, родителей, прошлую ссору и «ты всегда».',
        'Если тон уже стал главным предметом спора — остановиться на 20 минут и вернуться с одной конкретной просьбой.'
      ],
      notMeans: ['не значит, что кто-то глупее', 'не доказывает ложь или манипуляцию', 'не запрещает научиться слышать друг друга']
    };
  }

  function genericAspectDetail(a) {
    const aspect = aspectMeaning[a.symbol] || { name: a.kind, text: 'Этот аспект связывает две функции карты и делает их заметными именно во взаимодействии.' };
    const repairs = a.tone === 'bad'
      ? ['Сначала отделять факт от реакции: что произошло — и что каждый в этом услышал.', `Не пытаться решить контакт силой. Для ${aspect.name.toLowerCase()} важнее повторяемое правило, чем одно идеальное объяснение.`, 'Заранее договориться о паузе и способе возвращаться к теме.']
      : a.tone === 'mid'
        ? ['Не считать смену ритма признаком охлаждения или отказа.', 'Прямо уточнять ожидания перед значимыми ситуациями.', 'Оставлять пространство на перенастройку без поиска виноватого.']
        : ['Замечать и называть, что именно здесь получается хорошо.', 'Использовать эту сильную связь в сложных сферах пары.', 'Не считать лёгкость вечной: поддерживать её конкретными действиями.'];
    return {
      headline: a.short,
      intro: `Твоя функция «${a.a}» (${planetMeaning[a.a] || 'важная часть способа проявляться'}) встречается с функцией «${a.b}» партнёра (${planetMeaning[a.b] || 'важная часть его реакции'}). ${aspect.text}`,
      scenes: [['Как это уже может ощущаться', a.human], ['Узнаваемая сцена', a.scene], ['Когда контакт усиливается', `Особенно заметно, когда тема затрагивает ${planetMeaning[a.a] || a.a.toLowerCase()} и одновременно требует от партнёра включить ${planetMeaning[a.b] || a.b.toLowerCase()}.`]],
      repairs,
      notMeans: ['не описывает человека целиком', 'не гарантирует исход отношений', 'работает вместе с остальными контактами карты']
    };
  }

  window.openAspectFromTech = function openAspectFromTech(tech) {
    const compact = String(tech).replace(/\s/g, '');
    const index = current.aspects.findIndex(a => compact.includes((a.a + a.symbol + a.b).replace(/\s/g, '')));
    if (index >= 0) openAspectMeaning(index);
    else toast('Для этого сочетания подробный разбор появится следующим');
  };

  window.openAspectMeaning = function openAspectMeaning(index) {
    if (!current || !current.aspects[index]) return;
    highlightAspect(index);
    const a = current.aspects[index];
    const detail = a.a === 'Меркурий' && a.b === 'Меркурий' && a.symbol === '□' ? mercurySquareDetail() : genericAspectDetail(a);
    const aspect = aspectMeaning[a.symbol] || { name: a.kind };
    document.getElementById('aspectModalTitle').textContent = `${a.a} ${a.symbol} ${a.b}`;
    document.getElementById('aspectModalContent').innerHTML = `<div class="aspect-modal-hero">
      <div class="aspect-modal-symbol ${a.tone}">${a.symbol}</div>
      <div><h2>${detail.headline}</h2><div class="aspect-modal-meta">${aspect.name} · орб ${a.orb} · ${a.tone === 'good' ? 'поддерживающий' : a.tone === 'mid' ? 'неоднозначный' : 'напряжённый'} контакт</div></div>
    </div>
    <section class="meaning-section"><p class="meaning-section-title">Что именно соединяется</p><div class="planet-pair">
      <div class="planet-meaning"><div class="planet-owner">Твоя карта</div><strong>${planetGlyph[a.a] || ''} ${a.a}</strong><p>${planetMeaning[a.a] || 'Функция твоей карты.'}</p></div>
      <div class="planet-meaning partner"><div class="planet-owner">Карта партнёра · ${current.name}</div><strong>${planetGlyph[a.b] || ''} ${a.b}</strong><p>${planetMeaning[a.b] || 'Функция карты партнёра.'}</p></div>
    </div></section>
    <section class="meaning-section"><p class="meaning-section-title">Как работает ${aspect.name.toLowerCase()}</p><div class="meaning-card"><p>${detail.intro}</p></div></section>
    <section class="meaning-section"><p class="meaning-section-title">Как это проявляется в жизни</p><div class="life-scenes">${detail.scenes.map(scene => `<div class="life-scene"><b>${scene[0]}</b><span>${scene[1]}</span></div>`).join('')}</div></section>
    <section class="meaning-section"><p class="meaning-section-title">Что помогает</p><div class="repair-list">${detail.repairs.map((repair, i) => `<div class="repair-item"><span class="repair-num">${i + 1}</span><p>${repair}</p></div>`).join('')}</div></section>
    <section class="meaning-section"><p class="meaning-section-title">Важно: это не означает</p><div class="not-means">${detail.notMeans.map(text => `<span>${text}</span>`).join('')}</div></section>`;
    modal.classList.add('open');
    document.body.style.overflow = 'hidden';
    modal.querySelector('.aspect-sheet').scrollTop = 0;
  };

  window.closeAspectModal = function closeAspectModal() {
    modal.classList.remove('open');
    document.body.style.overflow = '';
  };

  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') closeAspectModal();
  });
})();
