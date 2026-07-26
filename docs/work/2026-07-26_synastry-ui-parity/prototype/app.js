(() => {
  const files = ['./data.js', './scenarios.js', './logic.js'];
  const load = (index) => {
    if (index >= files.length) return;
    const script = document.createElement('script');
    script.src = files[index];
    script.onload = () => load(index + 1);
    script.onerror = () => console.error('Не удалось загрузить', files[index]);
    document.head.appendChild(script);
  };
  load(0);
})();
