/* 语言切换：默认中文，选择存在 localStorage；地址栏 ?lang=en 可以直接进英文 */
(function () {
  var root = document.documentElement;
  var btn = document.getElementById('lang');
  var KEY = 'acp-lang';

  function read() {
    var v = null;
    try { v = localStorage.getItem(KEY); } catch (e) {}
    if (v !== 'zh' && v !== 'en') {
      var q = null;
      try { q = new URLSearchParams(location.search).get('lang'); } catch (e) {}
      v = (q === 'en' || q === 'zh') ? q : 'zh';
    }
    return v;
  }

  function apply(lang) {
    root.setAttribute('data-lang', lang);
    root.setAttribute('lang', lang === 'zh' ? 'zh-CN' : 'en');
    if (btn) {
      btn.textContent = lang === 'zh' ? 'EN' : '中文';
      btn.setAttribute('title', lang === 'zh' ? 'Switch to English' : '切换到中文');
    }
    try { localStorage.setItem(KEY, lang); } catch (e) {}
  }

  apply(read());

  if (btn) {
    btn.addEventListener('click', function () {
      apply(root.getAttribute('data-lang') === 'zh' ? 'en' : 'zh');
    });
  }
})();
