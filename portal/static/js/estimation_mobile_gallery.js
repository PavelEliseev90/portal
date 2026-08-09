(function (window, document) {
  'use strict';

  function getCookie(name) {
    const value = '; ' + document.cookie;
    const parts = value.split('; ' + name + '=');
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
  }

  function normalizeInputName(name) {
    return (name || '').trim();
  }

  const DEFAULT_TARGETS = {
    image_sts: { type_file: 'sts', label: 'СТС' },
    image_pts: { type_file: 'pts', label: 'ПТС' },
    image_run: { type_file: 'run', label: 'Пробег' },
    image_salon: { type_file: 'salon_all', label: 'Салон (общий)' },
    image_damage_salon: { type_file: 'salon_error', label: 'Повреждения салона' },
    photo_a1: { type_file: 'vnesh_car_all', file_number: 1, single_slot: true, label: 'Внешний осмотр 1' },
    photo_a2: { type_file: 'vnesh_car_all', file_number: 2, single_slot: true, label: 'Внешний осмотр 2' },
    photo_a3: { type_file: 'vnesh_car_all', file_number: 3, single_slot: true, label: 'Внешний осмотр 3' },
    photo_a4: { type_file: 'vnesh_car_all', file_number: 4, single_slot: true, label: 'Внешний осмотр 4' },
    photo_a5: { type_file: 'vnesh_car_all', file_number: 5, single_slot: true, label: 'Внешний осмотр 5' },
    photo_a6: { type_file: 'vnesh_car_all', file_number: 6, single_slot: true, label: 'Внешний осмотр 6' },
    photo_a7: { type_file: 'vnesh_car_all', file_number: 7, single_slot: true, label: 'Внешний осмотр 7' },
    photo_a8: { type_file: 'vnesh_car_all', file_number: 8, single_slot: true, label: 'Внешний осмотр 8' },
    file_light_error: { type_file: 'light_error', single_slot: true, label: 'Неисправность фар' },
    file_windshield_error: { type_file: 'windshield_error', single_slot: true, label: 'Неисправность лобового стекла' },
    file_vin: { type_file: 'vin', label: 'VIN' },
    file_podcapot: { type_file: 'pod_capot', label: 'Подкапотное пространство' },
    file_kolesa_1: { type_file: 'kolesa', label: 'Колёса (комплект 1)' },
    file_kolesa_2: { type_file: 'kolesa2', label: 'Колёса (комплект 2)' },
    file_gibdd: { type_file: 'gibdd', label: 'ГИБДД' },
    file_reestr: { type_file: 'reestr', label: 'Реестр залогов' },
    file_market: { type_file: 'market', label: 'Рынок' },
    file_epts: { type_file: 'epts', label: 'ЭПТС' },
    images_remote: { type_file: 'images_remote', label: 'Удалённая оценка' },
    file_reception_passport_spread: {
      type_file: 'reception_passport_spread',
      label: 'Скан паспорта — первый разворот',
    },
    file_reception_passport_registration: {
      type_file: 'reception_passport_registration',
      label: 'Скан паспорта — прописка',
    },
    file_reception_snils: { type_file: 'reception_snils', label: 'СНИЛС' },
    file_reception_pts: { type_file: 'reception_pts', label: 'ПТС (приём)' },
    file_reception_bankruptcy: {
      type_file: 'reception_bankruptcy',
      label: 'Проверка банкротства',
    },
    file_reception_fines: { type_file: 'reception_fines', label: 'Проверка штрафов' },
    file_reception_bailiffs: {
      type_file: 'reception_bailiffs',
      label: 'Проверка приставов',
    },
  };

  function EstimationMobileGallery(config) {
    this.rlkId = config.rlkId || '';
    this.estimationId = config.estimationId || '';
    this.inboxUrl = config.inboxUrl || '';
    this.assignUrl = config.assignUrl || '';
    this.deleteUrlBase = config.deleteUrlBase || '';
    this.qrUrl = config.qrUrl || '';
    this.uploadUrl = config.uploadUrl || '';
    this.osmotrSide = config.osmotrSide || '';
    this.targets = Object.assign({}, DEFAULT_TARGETS, config.targets || {});
    this.inboxFiles = [];
    this.assignContext = null;
    this.pendingOsmotrPoint = null;
    this.selectedOrder = [];
    this.pollTimer = null;
    this._bindUi();
    this.refreshInbox(true);
    this._enhanceFileInputs();
    this._startPolling();
  }

  EstimationMobileGallery.prototype._allowMultiple = function () {
    if (!this.assignContext) return true;
    if (this.assignContext.osmotr) return false;
    if (this.assignContext.allowMultiple === true) return true;
    if (this.assignContext.allowMultiple === false) return false;
    const target = this.assignContext.target || {};
    if (target.single_slot) return false;
    return true;
  };

  EstimationMobileGallery.prototype._bindUi = function () {
    const self = this;
    const panel = document.getElementById('mobile-gallery-panel');
    const toggleBtn = document.getElementById('mobile-gallery-toggle');
    const closeBtn = document.getElementById('mobile-gallery-close');
    const openModalBtn = document.getElementById('mobile-gallery-open-modal');
    const modalEl = document.getElementById('mobileGalleryModal');
    const assignBtn = document.getElementById('mobile-gallery-assign-btn');
    const deleteBtn = document.getElementById('mobile-gallery-delete-btn');
    const refreshBtn = document.getElementById('mobile-gallery-refresh-btn');
    const copyLinkBtn = document.getElementById('mobile-gallery-copy-link');

    if (toggleBtn && panel) {
      toggleBtn.addEventListener('click', function () {
        panel.classList.toggle('d-none');
      });
    }
    if (closeBtn && panel) {
      closeBtn.addEventListener('click', function () {
        panel.classList.add('d-none');
      });
    }
    if (openModalBtn && modalEl) {
      openModalBtn.addEventListener('click', function () {
        self.assignContext = null;
        self.selectedOrder = [];
        self._updateModalTitle('Галерея оценки');
        self._updateAssignButton();
        self._renderModalGrid();
        bootstrap.Modal.getOrCreateInstance(modalEl).show();
      });
    }
    if (refreshBtn) {
      refreshBtn.addEventListener('click', function () {
        self.refreshInbox(false);
      });
    }
    if (assignBtn) {
      assignBtn.addEventListener('click', function () {
        self._assignSelected();
      });
    }
    if (deleteBtn) {
      deleteBtn.addEventListener('click', function () {
        self._deleteSelected();
      });
    }
    if (copyLinkBtn && this.uploadUrl) {
      copyLinkBtn.addEventListener('click', function () {
        navigator.clipboard.writeText(self.uploadUrl).then(function () {
          self._toast('Ссылка скопирована');
        });
      });
    }
    if (modalEl) {
      modalEl.addEventListener('hidden.bs.modal', function () {
        self.assignContext = null;
        self.pendingOsmotrPoint = null;
        self.selectedOrder = [];
        self._updateAssignButton();
      });
    }
  };

  EstimationMobileGallery.prototype._startPolling = function () {
    const self = this;
    this.pollTimer = window.setInterval(function () {
      self.refreshInbox(true);
    }, 5000);
  };

  EstimationMobileGallery.prototype._enhanceFileInputs = function () {
    const self = this;
    document.querySelectorAll('input[type="file"]').forEach(function (input) {
      const inputName = normalizeInputName(input.name);
      const target = self.targets[inputName];
      if (!target) return;
      if (input.dataset.galleryEnhanced === '1') return;
      input.dataset.galleryEnhanced = '1';

      const wrap = document.createElement('div');
      wrap.className = 'mobile-gallery-file-wrap';
      input.parentNode.insertBefore(wrap, input);
      wrap.appendChild(input);

      const allowMultiple = !!(input.multiple || input.hasAttribute('multiple')) && !target.single_slot;
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'btn btn-outline-primary btn-sm w-100 mt-1 mobile-gallery-pick-btn';
      btn.innerHTML = allowMultiple
        ? '<span class="icon-mbri-image-slider"></span> Из галереи (несколько)'
        : '<span class="icon-mbri-image-slider"></span> Из галереи';
      btn.addEventListener('click', function () {
        self.openAssignModal(inputName, target, input, allowMultiple);
      });
      wrap.appendChild(btn);
    });
  };

  EstimationMobileGallery.prototype.openAssignModal = function (inputName, target, inputEl, allowMultiple) {
    this.assignContext = {
      inputName: inputName,
      target: target,
      inputEl: inputEl,
      allowMultiple: !!allowMultiple,
    };
    this.selectedOrder = [];
    this._updateModalTitle(
      allowMultiple
        ? 'Выберите фото для: ' + (target.label || inputName)
        : 'Привязать к: ' + (target.label || inputName)
    );
    this._updateAssignButton();
    this._renderModalGrid();
    const modalEl = document.getElementById('mobileGalleryModal');
    if (modalEl) bootstrap.Modal.getOrCreateInstance(modalEl).show();
  };

  EstimationMobileGallery.prototype.openOsmotrAssign = function (pointData) {
    this.pendingOsmotrPoint = pointData;
    this.assignContext = { osmotr: true, allowMultiple: false };
    this.selectedOrder = [];
    this._updateModalTitle('Выберите фото для точки осмотра');
    this._updateAssignButton();
    this._renderModalGrid();
    const modalEl = document.getElementById('mobileGalleryModal');
    if (modalEl) bootstrap.Modal.getOrCreateInstance(modalEl).show();
  };

  EstimationMobileGallery.prototype._updateModalTitle = function (title) {
    const el = document.getElementById('mobileGalleryModalLabel');
    if (el) el.textContent = title;
  };

  EstimationMobileGallery.prototype._updateAssignButton = function () {
    const assignBtn = document.getElementById('mobile-gallery-assign-btn');
    if (!assignBtn) return;
    const multi = this._allowMultiple() && this.assignContext && this.assignContext.target;
    const count = this.selectedOrder.length;
    if (multi && count > 0) {
      assignBtn.classList.remove('d-none');
      assignBtn.textContent = 'Привязать (' + count + ')';
      assignBtn.disabled = false;
    } else if (multi) {
      assignBtn.classList.remove('d-none');
      assignBtn.textContent = 'Привязать';
      assignBtn.disabled = true;
    } else {
      assignBtn.classList.add('d-none');
      assignBtn.disabled = true;
    }
  };

  EstimationMobileGallery.prototype.refreshInbox = function (silent) {
    const self = this;
    if (!this.inboxUrl) return Promise.resolve();
    return fetch(this.inboxUrl, { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.ok) return;
        self.inboxFiles = data.files || [];
        if (data.upload_url) self.uploadUrl = data.upload_url;
        self._updateBadge(self.inboxFiles.length);
        const modalEl = document.getElementById('mobileGalleryModal');
        if (modalEl && modalEl.classList.contains('show') && !silent) {
          self._renderModalGrid();
        }
      })
      .catch(function () { /* ignore polling errors */ });
  };

  EstimationMobileGallery.prototype._updateBadge = function (count) {
    const badge = document.getElementById('mobile-gallery-count');
    const floatBtn = document.getElementById('mobile-gallery-float-btn');
    if (badge) badge.textContent = count;
    if (floatBtn) {
      floatBtn.classList.toggle('has-photos', count > 0);
      floatBtn.title = count > 0 ? ('Галерея: ' + count + ' фото') : 'Галерея оценки';
    }
  };

  EstimationMobileGallery.prototype._toggleSelect = function (fileId) {
    const id = parseInt(fileId, 10);
    const idx = this.selectedOrder.indexOf(id);
    if (idx >= 0) {
      this.selectedOrder.splice(idx, 1);
    } else {
      this.selectedOrder.push(id);
    }
    this._paintSelectionBadges();
    this._updateAssignButton();
  };

  EstimationMobileGallery.prototype._paintSelectionBadges = function () {
    const self = this;
    document.querySelectorAll('#mobile-gallery-grid .mobile-gallery-thumb').forEach(function (el) {
      const id = parseInt(el.dataset.fileId, 10);
      const order = self.selectedOrder.indexOf(id);
      const badge = el.querySelector('.mobile-gallery-order');
      if (order >= 0) {
        el.classList.add('selected');
        if (badge) {
          badge.textContent = String(order + 1);
          badge.classList.remove('d-none');
        }
      } else {
        el.classList.remove('selected');
        if (badge) {
          badge.textContent = '';
          badge.classList.add('d-none');
        }
      }
    });
  };

  EstimationMobileGallery.prototype._renderModalGrid = function () {
    const grid = document.getElementById('mobile-gallery-grid');
    const empty = document.getElementById('mobile-gallery-empty');
    if (!grid) return;
    grid.innerHTML = '';
    if (!this.inboxFiles.length) {
      if (empty) empty.classList.remove('d-none');
      this._updateAssignButton();
      return;
    }
    if (empty) empty.classList.add('d-none');

    const self = this;
    const multi = this._allowMultiple();
    const hasAssignContext = !!(this.assignContext && (this.assignContext.target || this.assignContext.osmotr));

    // Keep selection only for files still in inbox
    const inboxIds = {};
    this.inboxFiles.forEach(function (f) { inboxIds[f.id] = true; });
    this.selectedOrder = this.selectedOrder.filter(function (id) { return inboxIds[id]; });

    this.inboxFiles.forEach(function (file) {
      const col = document.createElement('div');
      col.className = 'col-4 col-sm-3 col-md-2';

      const card = document.createElement('button');
      card.type = 'button';
      card.className = 'mobile-gallery-thumb card h-100';
      card.dataset.fileId = file.id;
      card.innerHTML =
        '<span class="mobile-gallery-order d-none"></span>' +
        '<img src="' + (file.thumb_url || file.url) + '" alt="" class="card-img-top">' +
        '<div class="card-body p-1"><div class="small text-truncate">' + (file.date || '') + '</div></div>';

      card.addEventListener('click', function () {
        if (hasAssignContext && !multi) {
          self.selectedOrder = [file.id];
          self._paintSelectionBadges();
          self._assignOne(file.id)
            .then(function (data) {
              self._onAssignSuccess(data, true);
            })
            .catch(function (err) {
              self._toast(err.message || 'Ошибка', true);
            });
          return;
        }
        self._toggleSelect(file.id);
      });
      col.appendChild(card);
      grid.appendChild(col);
    });
    this._paintSelectionBadges();
    this._updateAssignButton();
  };

  EstimationMobileGallery.prototype._getSelectedIds = function () {
    if (this.selectedOrder && this.selectedOrder.length) {
      return this.selectedOrder.slice();
    }
    const ids = [];
    document.querySelectorAll('#mobile-gallery-grid .mobile-gallery-thumb.selected').forEach(function (el) {
      if (el.dataset.fileId) ids.push(parseInt(el.dataset.fileId, 10));
    });
    return ids;
  };

  EstimationMobileGallery.prototype._assignOne = function (fileId) {
    const self = this;
    let payload = { inbox_id: fileId };

    if (this.assignContext && this.assignContext.osmotr && this.pendingOsmotrPoint) {
      payload = Object.assign(payload, {
        osmotr_side: this.osmotrSide,
        type_point: this.pendingOsmotrPoint.type_point,
        text: this.pendingOsmotrPoint.text,
        cor_x: this.pendingOsmotrPoint.cor_x,
        cor_y: this.pendingOsmotrPoint.cor_y,
        kraska: this.pendingOsmotrPoint.kraska || 0,
      });
    } else if (this.assignContext && this.assignContext.target) {
      payload.input_name = this.assignContext.inputName;
      payload.target = this.assignContext.target;
    } else {
      return Promise.reject(new Error('Не выбран раздел'));
    }

    return fetch(this.assignUrl, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken'),
      },
      body: JSON.stringify(payload),
    })
      .then(function (r) {
        return r.text().then(function (t) {
          let data = null;
          try {
            data = t ? JSON.parse(t) : null;
          } catch (e) {
            throw new Error('Сервер ответил не JSON. Пример ответа: ' + (t || '').slice(0, 200));
          }
          return { ok: r.ok, data: data };
        });
      })
      .then(function (res) {
        if (!res.ok || !res.data.ok) {
          throw new Error((res.data && res.data.error) || 'Не удалось привязать фото');
        }
        return res.data;
      });
  };

  EstimationMobileGallery.prototype._assignSelected = function () {
    const self = this;
    const ids = this._getSelectedIds();
    if (!ids.length) {
      this._toast('Выберите фото', true);
      return;
    }
    if (!(this.assignContext && this.assignContext.target)) {
      this._toast('Откройте привязку через кнопку «Из галереи» у нужного раздела', true);
      return;
    }

    const multi = this._allowMultiple();
    if (!multi) {
      this._assignOne(ids[0])
        .then(function (data) {
          self._onAssignSuccess(data, true);
        })
        .catch(function (err) {
          self._toast(err.message || 'Ошибка', true);
        });
      return;
    }

    const assignBtn = document.getElementById('mobile-gallery-assign-btn');
    if (assignBtn) assignBtn.disabled = true;
    let done = 0;
    const total = ids.length;
    const assigned = [];

    const runNext = function (index) {
      if (index >= ids.length) {
        self._toast('Привязано фото: ' + done + ' из ' + total);
        self._updateBadge(self.inboxFiles.length - done);
        self.selectedOrder = [];
        if (self._isReceptionTarget()) {
          self._reloadReceptionPage();
          return;
        }
        self.refreshInbox(true).then(function () {
          const modalEl = document.getElementById('mobileGalleryModal');
          if (modalEl) bootstrap.Modal.getOrCreateInstance(modalEl).hide();
        });
        if (self.assignContext && self.assignContext.inputEl && assigned.length) {
          self._showAssignedPreviewMany(self.assignContext.inputEl, assigned);
        }
        return;
      }
      self._toast('Привязка ' + (index + 1) + ' / ' + total + '…');
      self._assignOne(ids[index])
        .then(function (data) {
          done += 1;
          if (data && data.file) assigned.push(data.file);
          if (typeof data.inbox_count === 'number') self._updateBadge(data.inbox_count);
          runNext(index + 1);
        })
        .catch(function (err) {
          self._toast((err && err.message) || 'Ошибка на фото ' + (index + 1), true);
          if (assignBtn) assignBtn.disabled = false;
          self.refreshInbox(false);
        });
    };
    runNext(0);
  };

  EstimationMobileGallery.prototype._isReceptionTarget = function () {
    const target = this.assignContext && this.assignContext.target;
    const typeFile = (target && target.type_file) || '';
    return String(typeFile).indexOf('reception_') === 0;
  };

  EstimationMobileGallery.prototype._reloadReceptionPage = function () {
    try {
      const url = new URL(window.location.href);
      url.searchParams.set('page', '24');
      window.location.href = url.href;
    } catch (e) {
      window.location.reload();
    }
  };

  EstimationMobileGallery.prototype._onAssignSuccess = function (data, closeModal) {
    this._toast((data && data.message) || 'Фото привязано');
    if (data && typeof data.inbox_count === 'number') this._updateBadge(data.inbox_count);
    this.refreshInbox(true);
    if (closeModal) {
      const modalEl = document.getElementById('mobileGalleryModal');
      if (modalEl) bootstrap.Modal.getOrCreateInstance(modalEl).hide();
    }
    if (this._isReceptionTarget()) {
      this._reloadReceptionPage();
      return;
    }
    if (this.assignContext && this.assignContext.inputEl && data && data.file) {
      this._showAssignedPreview(this.assignContext.inputEl, data.file);
    }
    if (this.assignContext && this.assignContext.osmotr && window.mobileGalleryOsmotrAssigned) {
      window.mobileGalleryOsmotrAssigned(data.file, this.pendingOsmotrPoint);
    }
  };

  EstimationMobileGallery.prototype._deleteSelected = function () {
    const self = this;
    const ids = this._getSelectedIds();
    if (!ids.length) {
      this._toast('Выберите фото для удаления', true);
      return;
    }
    Promise.all(ids.map(function (id) {
      return fetch(self.deleteUrlBase + id + '/', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
      }).then(function (r) {
        return r.text().then(function (t) {
          try {
            return t ? JSON.parse(t) : { ok: true };
          } catch (e) {
            throw new Error('Некорректный ответ при удалении: ' + (t || '').slice(0, 200));
          }
        });
      });
    })).then(function () {
      self.selectedOrder = [];
      self._toast('Удалено');
      self.refreshInbox(false);
    }).catch(function (err) {
      self._toast(err.message || 'Ошибка удаления', true);
    });
  };

  EstimationMobileGallery.prototype._showAssignedPreview = function (inputEl, file) {
    this._showAssignedPreviewMany(inputEl, [file]);
  };

  EstimationMobileGallery.prototype._showAssignedPreviewMany = function (inputEl, files) {
    let preview = inputEl.parentNode.querySelector('.mobile-gallery-assigned-preview');
    if (!preview) {
      preview = document.createElement('div');
      preview.className = 'mobile-gallery-assigned-preview mt-2';
      inputEl.parentNode.appendChild(preview);
    }
    const thumbs = (files || []).slice(0, 8).map(function (file) {
      return '<img src="' + (file.thumb_url || file.url) + '" style="width:48px;height:48px;object-fit:cover;border-radius:8px;" alt="">';
    }).join('');
    preview.innerHTML =
      '<div class="d-flex align-items-center gap-2 p-2 border rounded bg-light flex-wrap">' +
      thumbs +
      '<div class="small text-success">Привязано: ' + (files || []).length + '. Сохраните раздел.</div></div>';
  };

  EstimationMobileGallery.prototype._toast = function (message, isError) {
    let toast = document.getElementById('mobile-gallery-toast');
    if (!toast) {
      toast = document.createElement('div');
      toast.id = 'mobile-gallery-toast';
      toast.className = 'mobile-gallery-toast';
      document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.className = 'mobile-gallery-toast show' + (isError ? ' error' : '');
    window.clearTimeout(this._toastTimer);
    this._toastTimer = window.setTimeout(function () {
      toast.classList.remove('show');
    }, 2800);
  };

  window.initEstimationMobileGallery = function (config) {
    window.estimationMobileGallery = new EstimationMobileGallery(config);
    return window.estimationMobileGallery;
  };
})(window, document);
