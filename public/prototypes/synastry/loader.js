(async () => {
  const response = await fetch('./base.html', { cache: 'no-store' });
  if (!response.ok) throw new Error(`Не удалось загрузить базовый прототип: ${response.status}`);
  let html = await response.text();
  html = html.replace('</head>', '<link rel="stylesheet" href="./aspect-drilldown.css"></head>');
  html = html.replace('</body>', '<script src="./aspect-drilldown.js"></' + 'script></body>');
  document.open();
  document.write(html);
  document.close();
})().catch(error => {
  document.body.innerHTML = `<main style="font-family:system-ui;padding:32px"><h1>Не удалось открыть прототип</h1><p>${error.message}</p></main>`;
  console.error(error);
});