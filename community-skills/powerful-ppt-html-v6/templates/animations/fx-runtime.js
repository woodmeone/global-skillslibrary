(function () {
  'use strict';

  var FX_LIST = [
    '_util',
    'particle-burst', 'confetti-cannon', 'firework', 'starfield', 'matrix-rain',
    'knowledge-graph', 'neural-net', 'constellation', 'orbit-ring', 'galaxy-swirl',
    'word-cascade', 'letter-explode', 'chain-react', 'magnetic-field', 'data-stream',
    'gradient-blob', 'sparkle-trail', 'shockwave', 'typewriter-multi', 'counter-explosion'
  ];

  var myScript = document.currentScript || (function () {
    var all = document.getElementsByTagName('script');
    for (var i = 0; i < all.length; i++) {
      if (all[i].src && all[i].src.indexOf('fx-runtime.js') > -1) return all[i];
    }
    return null;
  })();
  var base = myScript ? myScript.src.replace(/fx-runtime\.js.*$/, 'fx/') : 'templates/animations/fx/';

  var loaded = 0;
  var total = FX_LIST.length;
  var ready = new Promise(function (resolve) {
    if (!total) return resolve();
    FX_LIST.forEach(function (name) {
      var s = document.createElement('script');
      s.src = base + name + '.js';
      s.async = false;
      s.onload = s.onerror = function () { if (++loaded >= total) resolve(); };
      document.head.appendChild(s);
    });
  });

  window.__ppxActive = window.__ppxActive || new Map();

  function initFxIn(root) {
    if (!window.PPX) return;
    var els = root.querySelectorAll('[data-fx]');
    els.forEach(function (el) {
      if (window.__ppxActive.has(el)) return;
      var name = el.getAttribute('data-fx');
      var fn = window.PPX[name];
      if (typeof fn !== 'function') return;
      try {
        var handle = fn(el, {}) || { stop: function () { } };
        window.__ppxActive.set(el, handle);
      } catch (e) { console.warn('[ppx-fx]', name, e); }
    });
  }

  function stopFxIn(root) {
    var els = root.querySelectorAll('[data-fx]');
    els.forEach(function (el) {
      var h = window.__ppxActive.get(el);
      if (h && typeof h.stop === 'function') {
        try { h.stop(); } catch (e) { }
      }
      window.__ppxActive.delete(el);
    });
  }

  function reinitFxIn(root) {
    stopFxIn(root);
    initFxIn(root);
  }
  window.__ppxReinit = reinitFxIn;

  function boot() {
    ready.then(function () {
      var active = document.querySelector('.slide.active') || document.querySelector('.slide');
      if (active) initFxIn(active);

      var slides = document.querySelectorAll('.slide');
      slides.forEach(function (sl) {
        var mo = new MutationObserver(function (muts) {
          for (var i = 0; i < muts.length; i++) {
            if (muts[i].attributeName === 'class') {
              if (sl.classList.contains('active')) initFxIn(sl);
              else stopFxIn(sl);
            }
          }
        });
        mo.observe(sl, { attributes: true, attributeFilter: ['class'] });
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
