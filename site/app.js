(() => {
  const switcher = document.getElementById('language-switch');
  const params = new URLSearchParams(window.location.search);
  const requested = params.get('lang');
  const initial = requested === 'zh' ? 'zh' : 'en';

  function setLanguage(lang) {
    document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';
    for (const node of document.querySelectorAll('[data-en][data-zh]')) {
      const value = node.getAttribute(lang === 'zh' ? 'data-zh' : 'data-en');
      if (value.includes('<br>') || value.includes('<em>')) node.innerHTML = value;
      else node.textContent = value;
    }
    switcher.textContent = lang === 'zh' ? 'EN' : '中文';
    switcher.setAttribute('aria-label', lang === 'zh' ? 'Switch to English' : '切换为中文');
    document.title = lang === 'zh' ? '睿禾健康 — 每一步都有依据' : 'ReHealth AI — Health trends, with evidence attached';
  }

  setLanguage(initial);
  switcher.addEventListener('click', () => setLanguage(document.documentElement.lang === 'zh-CN' ? 'en' : 'zh'));
})();
