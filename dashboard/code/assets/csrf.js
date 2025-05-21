// assets/csrf.js
(function() {
  const token = document.querySelector('meta[name="csrf-token"]').content;
  // override fetch to always include X-CSRFToken
  const _fetch = window.fetch;
  window.fetch = function(input, init = {}) {
    init.headers = Object.assign(init.headers || {}, {
      'X-CSRFToken': token
    });
    return _fetch(input, init);
  };
})();
