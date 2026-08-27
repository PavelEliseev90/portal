/**
 * Универсальный мультивыбор с поиском (подразделения и др.).
 * Разметка: data-portal-mcf="prefix"
 *   #{prefix}Search, #{prefix}Dropdown, #{prefix}Selected
 */
(function (global) {
  'use strict';

  function escapeHtml(s) {
    return String(s || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function initOne(prefix) {
    var search = document.getElementById(prefix + 'Search');
    var dropdown = document.getElementById(prefix + 'Dropdown');
    var selectedDiv = document.getElementById(prefix + 'Selected');
    if (!search || !dropdown || !selectedDiv) return;
    if (search.getAttribute('data-portal-mcf-ready') === '1') return;
    search.setAttribute('data-portal-mcf-ready', '1');

    function updateSelected() {
      var checked = dropdown.querySelectorAll('input[type="checkbox"]:checked');
      selectedDiv.innerHTML = '';
      if (!checked.length) return;
      selectedDiv.innerHTML = Array.prototype.map.call(checked, function (cb) {
        var label = cb.closest('label');
        var text = label ? label.textContent.trim().replace(/\s+/g, ' ') : cb.value;
        return (
          '<span class="badge bg-primary me-1 mb-1" style="font-size: 0.85em;">' +
          escapeHtml(text) +
          ' <button type="button" class="btn-close btn-close-white ms-1 portal-mcf-remove" style="font-size: 0.65em;"' +
          ' data-cb-name="' + escapeHtml(cb.name) + '"' +
          ' data-cb-value="' + escapeHtml(cb.value) + '"></button></span>'
        );
      }).join('');
    }

    selectedDiv.addEventListener('click', function (e) {
      var btn = e.target.closest('.portal-mcf-remove');
      if (!btn) return;
      var nm = btn.getAttribute('data-cb-name');
      var val = btn.getAttribute('data-cb-value');
      dropdown.querySelectorAll('input[type="checkbox"]').forEach(function (inp) {
        if (inp.name === nm && inp.value === val) inp.checked = false;
      });
      updateSelected();
    });

    search.addEventListener('input', function () {
      var term = (this.value || '').toLowerCase().trim();
      dropdown.querySelectorAll('label.list-group-item').forEach(function (item) {
        var text = (item.textContent || '').toLowerCase();
        item.style.display = !term || text.indexOf(term) !== -1 ? '' : 'none';
      });
    });

    search.addEventListener('focus', function () {
      dropdown.style.display = 'block';
    });

    dropdown.addEventListener('mousedown', function (e) {
      e.preventDefault();
    });

    document.addEventListener('click', function (e) {
      if (
        !search.contains(e.target) &&
        !dropdown.contains(e.target) &&
        !selectedDiv.contains(e.target)
      ) {
        dropdown.style.display = 'none';
      }
    });

    dropdown.querySelectorAll('input[type="checkbox"]').forEach(function (cb) {
      cb.addEventListener('change', updateSelected);
    });

    updateSelected();
  }

  function initAll(root) {
    var scope = root || document;
    scope.querySelectorAll('[data-portal-mcf]').forEach(function (el) {
      var prefix = el.getAttribute('data-portal-mcf');
      if (prefix) initOne(prefix);
    });
  }

  global.PortalMultiCheckboxFilter = {
    init: initOne,
    initAll: initAll,
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      initAll();
    });
  } else {
    initAll();
  }
})(window);
