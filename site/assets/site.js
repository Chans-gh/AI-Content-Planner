/* 语言切换：默认中文，选择存在 localStorage；地址栏 ?lang=en 可以直接进英文。
   按钮上的两段文字由 CSS 按 html[data-lang] 切换，这里只改属性。 */
(function () {
  var root = document.documentElement;
  var btn = document.getElementById('lang-toggle');
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
    try { localStorage.setItem(KEY, lang); } catch (e) {}
  }

  apply(read());

  if (btn) {
    btn.addEventListener('click', function () {
      apply(root.getAttribute('data-lang') === 'zh' ? 'en' : 'zh');
    });
  }
})();
