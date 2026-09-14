/**
 * AUCTION DOCUMENT COCKPIT (auction-doc.js)
 * Modern dynamic calculations, car picker offcanvas, car studio tabs, and media management.
 */

var store_id = '';
var page = 0;
var scroll_data = true;

$(document).ready(function() {
    initTabs();
    initCopyButtons();
    initMainPhotoSelection();
    initLightbox();
    initStoreCombo();
    initDateTimePicker();
    refresh_board();
    initAuctionBids();

    // Price input real-time calculation
    $('#price_start').on('input change', function() {
        refresh_board();
    });

    // Min price click to fill
    $(document).on('click', '#min_price_chip', function() {
        var minVal = $(this).data('min-val');
        if (minVal !== undefined && minVal !== null) {
            $('#price_start').val(minVal).trigger('input');
        }
    });

    // Edit car modal opener
    $(document).on('click', '[id^="edit_car_info_"]', function() {
        var id = this.id.replace('edit_car_info_', '');
        var modalId = 'cars_list_data_slug_' + id + '_modal';
        $('#' + modalId).modal('show');
    });

    // Add cars trigger (opens offcanvas)
    $('#add_cars').on('click', function() {
        store_id = $('select#store option:selected').val() || $('select#store option:selected').attr('text') || '';

        if (!store_id) {
            showAuctionToast('Пожалуйста, выберите стоянку перед добавлением автомобиля', 'Внимание', 'warning');
            $('select#store').focus();
            return;
        }

        var carsList = document.querySelector('#cars-list');
        if (carsList) carsList.innerHTML = '';

        page = 0;
        visible_loader(true);
        refresh_data_online();
        visible_canvas();
    });

    // Search offcanvas refresh
    $('#refresh').on('click', function() {
        page = 0;
        scroll_data = true;
        visible_loader(true);
        var carsList = document.querySelector('#cars-list');
        if (carsList) carsList.innerHTML = '';
        refresh_data_online();
    });

    // Search offcanvas pagination
    $('#more').on('click', function() {
        page = page + 1;
        visible_loader(true);
        refresh_data_online();
    });

    // Search input debounced
    var searchTimer = null;
    $('#search').on('input', function() {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(function() {
            page = 0;
            var carsList = document.querySelector('#cars-list');
            if (carsList) carsList.innerHTML = '';
            visible_loader(true);
            refresh_data_online();
        }, 350);
    });

    // Offcanvas events
    var offcanvasEl = document.getElementById('offcanvasRight');
    if (offcanvasEl) {
        offcanvasEl.addEventListener('hide.bs.offcanvas', function() {
            $('#cars-list').addClass('fade-out');
        });
        offcanvasEl.addEventListener('hidden.bs.offcanvas', function() {
            $('#cars-list').empty().removeClass('fade-out');
            page = 0;
        });
        offcanvasEl.addEventListener('shown.bs.offcanvas', function() {
            $('#cars-list').removeClass('fade-out');
            $('#search').focus();
        });
    }
});

/* ==========================================================================
   TABS INITIALIZATION
   ========================================================================== */
function initTabs() {
    $(document).on('click', '.ad-tab-btn', function() {
        var $btn = $(this);
        var targetId = $btn.data('target');
        var $modal = $btn.closest('.modal');

        $modal.find('.ad-tab-btn').removeClass('active');
        $btn.addClass('active');

        $modal.find('.ad-tab-pane').removeClass('active');
        $modal.find('#' + targetId).addClass('active');
    });
}

/* ==========================================================================
   LIGHTBOX PHOTO ZOOM
   ========================================================================== */
function initLightbox() {
    // Append lightbox modal if not exists
    if (!$('#ad_lightbox_modal').length) {
        var modalHtml = `
        <div class="modal fade" id="ad_lightbox_modal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered modal-xl">
                <div class="modal-content" style="background: rgba(10, 11, 15, 0.95) !important; border: 1px solid var(--ad-border) !important;">
                    <div class="modal-header" style="background: transparent !important; border: none !important;">
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Закрыть"></button>
                    </div>
                    <div class="modal-body text-center p-2">
                        <img src="" id="ad_lightbox_img" class="ad-lightbox-img" alt="Фото автомобиля">
                    </div>
                </div>
            </div>
        </div>`;
        $('body').append(modalHtml);
    }

    $(document).on('click', '.ad-photo-tile__img-wrap img, .ad-car-thumb img', function(e) {
        e.stopPropagation();
        var src = $(this).attr('src');
        if (src && src !== '/media/nophoto.png') {
            $('#ad_lightbox_img').attr('src', src);
            $('#ad_lightbox_modal').modal('show');
        }
    });
}

/* ==========================================================================
   CLIPBOARD COPY HELPER
   ========================================================================== */
function initCopyButtons() {
    $(document).on('click', '.ad-copy-btn', function(e) {
        e.preventDefault();
        e.stopPropagation();
        var text = $(this).data('copy');
        if (!text) return;

        navigator.clipboard.writeText(text).then(function() {
            showAuctionToast('Скопировано в буфер: ' + text, 'Успешно', 'success');
        }).catch(function() {
            showAuctionToast('Не удалось скопировать', 'Ошибка', 'danger');
        });
    });
}

/* ==========================================================================
   MAIN PHOTO TOGGLING
   ========================================================================== */
function initMainPhotoSelection() {
    $(document).on('click', '.check_glav', function() {
        var id = this.id;
        if (id && id.indexOf('photo_vnesh_glav') !== -1) {
            var prefix = id.split('_photo_vnesh_glav')[0] + '_photo_vnesh_glav';
            clearMainPhotos(id, prefix);
        }
    });

    $(document).on('click', '.ad-star-btn', function(e) {
        e.preventDefault();
        e.stopPropagation();
        var targetInputId = $(this).data('input-id');
        var $input = $('#' + targetInputId);
        if ($input.length) {
            $input.prop('checked', true).trigger('change');
            var prefix = targetInputId.split('_photo_vnesh_glav')[0] + '_photo_vnesh_glav';
            clearMainPhotos(targetInputId, prefix);

            // Update star visuals in the same gallery
            var $modal = $(this).closest('.modal');
            $modal.find('.ad-star-btn').removeClass('is-active').html('☆');
            $(this).addClass('is-active').html('★');
        }
    });
}

function clearMainPhotos(selectedId, prefix) {
    $('input:checkbox').each(function() {
        if (this.id && this.id.indexOf(prefix) !== -1) {
            if (this.id !== selectedId) {
                $(this).prop('checked', false);
            }
        }
    });
}

/* ==========================================================================
   BOARD REFRESH & KPI CALCULATIONS
   ========================================================================== */
function refresh_board() {
    var price_lot = parseFloat($('#price_start').val()) || 0;
    var carCards = $('[id*="cars_list_data_id_"]');
    var count_car = carCards.length;

    var price_cars = 0;
    var cost_price_cars = 0;
    var outlay_cars = 0;

    carCards.each(function() {
        var id = this.id.replace('cars_list_data_id_', '');
        var price = parseFloat($('#cars_list_data_price_' + id).val()) || 0;
        var cost = parseFloat($('#cars_list_data_cost_price_' + id).val()) || 0;
        var outlay = parseFloat($('#cars_list_data_outlay_' + id).val()) || 0;

        price_cars += price;
        cost_price_cars += cost;
        outlay_cars += outlay;
    });

    var formatter = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 });

    var price_cars_str = formatter.format(price_cars);
    var cost_price_cars_str = formatter.format(cost_price_cars);
    var outlay_cars_str = formatter.format(outlay_cars);

    // Update KPI card values (supporting both legacy and new IDs)
    $('#car_count, #car_count_val').text(count_car + ' шт.');
    $('#car_cost_price, #car_cost_price_val').text(cost_price_cars_str + ' ₽');
    $('#car_outlay, #car_outlay_val').text(outlay_cars_str + ' ₽');
    $('#car_price, #car_price_val').text(price_cars_str + ' ₽');

    // Net Profit
    var car_profit_int = price_cars - cost_price_cars - outlay_cars;
    var car_profit_str = formatter.format(car_profit_int);
    var $profitEl = $('#car_profit, #car_profit_val');
    $profitEl.text(car_profit_str + ' ₽');
    $profitEl.removeClass('is-positive is-negative').addClass(car_profit_int >= 0 ? 'is-positive' : 'is-negative');

    // Auction Profit
    var car_profit_auction_int = price_lot - cost_price_cars - outlay_cars;
    var car_profit_auction_str = formatter.format(car_profit_auction_int);
    var $profitAuctionEl = $('#car_profit_auction, #car_profit_auction_val');
    $profitAuctionEl.text(car_profit_auction_str + ' ₽');
    $profitAuctionEl.removeClass('is-positive is-negative').addClass(car_profit_auction_int >= 0 ? 'is-positive' : 'is-negative');

    // Start Price minimum enforcement
    $('#price_start').attr('min', price_cars);
    $('#min_price_start').html('Мин. стартовая цена: <span class="ad-min-price-chip" id="min_price_chip" data-min-val="' + price_cars + '">' + price_cars_str + ' ₽</span>');

    // Fleet Counter in deck header
    $('#total_cars_count').text(count_car);

    // Empty state and action buttons toggles
    if (count_car > 0) {
        $('#no_cars').addClass('d-none');
        $('#save').removeClass('d-none');
        $('#send').removeClass('d-none');
        $('#update').removeClass('d-none');
    } else {
        $('#no_cars').removeClass('d-none');
        $('#save').addClass('d-none');
        $('#send').addClass('d-none');
        $('#update').addClass('d-none');
    }
}

/* ==========================================================================
   ADD & DELETE CARS
   ========================================================================== */
function subbmit_car(slug) {
    var count_car = $('#cars_list_data_id_' + slug).length;

    if (count_car > 0) {
        showAuctionToast('Автомобиль уже добавлен в лот аукциона!', 'Внимание', 'warning');
        return;
    }

    var url = '/auction/js/get_cars_lot_online/' + slug + '/';
    $.get(url, function(data) {
        if (!Array.isArray(data)) {
            data = data ? [data] : [];
        }
        if (!data.length) {
            showAuctionToast('Не удалось загрузить данные по автомобилю', 'Ошибка', 'danger');
            return;
        }

        var obj = data[0];
        var mark = obj.mark_name || '';
        var model = obj.model_name || '';
        var mod = obj.modification_name || '';
        var id = obj.slug;
        var photo0 = (obj.url && obj.url.length) ? obj.url[0] : '/media/nophoto.png';

        var fmt = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 });
        var car_run = fmt.format(obj.run || 0);
        var car_price = fmt.format(obj.price || 0);
        var car_cost = fmt.format(obj.cost_price || 0);
        var car_outlay = fmt.format(obj.outlay || 0);
        var car_bcp = fmt.format(obj.bcp || 0);

        var html_card = `
        <div class="ad-car-card" id="cars_list_data_id_${id}">
            <div class="ad-car-main">
                <div class="ad-car-thumb">
                    <img src="${photo0}" alt="${mark} ${model}">
                </div>
                <div class="ad-car-details">
                    <h3 class="ad-car-title">${mark} ${model}</h3>
                    <div class="ad-car-modification">${mod}</div>
                    <div class="ad-car-chips">
                        <span class="ad-car-chip">${obj.year} г.в.</span>
                        <span class="ad-car-chip ad-car-chip--mono">${car_run} км</span>
                        <span class="ad-car-chip ad-car-chip--mono">VIN: ${obj.vin || '-'}</span>
                    </div>
                </div>
                <div class="ad-car-finance">
                    <div class="ad-car-finance-item">
                        <span>Себестоимость:</span>
                        <span>${car_cost} ₽</span>
                    </div>
                    <div class="ad-car-finance-item">
                        <span>Затраты:</span>
                        <span>${car_outlay} ₽</span>
                    </div>
                    <div class="ad-car-finance-item">
                        <span>БЦП:</span>
                        <span>${car_bcp} ₽</span>
                    </div>
                    <div class="ad-car-finance-item ad-car-finance-item--sale">
                        <span>Продажа:</span>
                        <span>${car_price} ₽</span>
                    </div>
                </div>
            </div>

            <div class="ad-car-footer">
                <div class="ad-car-links">
                    <span class="ad-status-pill is-draft">
                        <span class="ad-status-dot"></span> Требует сохранения
                    </span>
                    <a class="ad-car-ext-btn" href="/cars/${id}/" target="_blank" rel="noopener">
                        <span class="icon-mbri-preview"></span> Карточка авто
                    </a>
                    ${obj.rlk_id ? `<a class="ad-car-ext-btn" href="/eco/${obj.rlk_id}/" target="_blank" rel="noopener"><span class="icon-mbri-search"></span> Оценка</a>` : ''}
                </div>
                <div class="ad-car-actions">
                    <button type="button" class="ad-btn ad-btn--outline ad-btn--sm" id="edit_car_info_${id}">
                        <span class="icon-mbri-edit"></span> Настроить
                    </button>
                    <button type="button" class="ad-btn ad-btn--danger-outline ad-btn--sm" onclick="delete_car('${id}')" title="Удалить из лота">
                        <span class="icon-mbri-trash"></span>
                    </button>
                </div>
            </div>

            <input hidden id="cars_list_data_cost_price_${id}" value="${obj.cost_price}">
            <input hidden id="cars_list_data_price_${id}" value="${obj.price}">
            <input hidden id="cars_list_data_outlay_${id}" value="${obj.outlay}">
            <input hidden name="cars_list_data_slug_${id}" value="${id}">
            <input hidden name="cars_list_data_op${id}" value="${obj.description_op || ''}">
            <input hidden name="cars_list_data_pod${id}" value="${obj.description_podgotovka || ''}">
            <input hidden name="cars_list_data_diag${id}" value="${obj.int_ocenka_diagnostika || ''}">
            <input hidden name="cars_list_data_work${id}" value="${obj.work || ''}">
        </div>`;

        var modal_html = `
        <div class="modal fade" id="cars_list_data_slug_${id}_modal" data-bs-backdrop="static" data-bs-keyboard="false" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-xl modal-dialog-scrollable">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <span class="icon-truck"></span> ${mark} ${model} • ${obj.year} • ${obj.vin || ''}
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Закрыть"></button>
                    </div>
                    <div class="modal-body">
                        <div class="alert alert-warning bg-opacity-10 text-white border-warning">
                            Полное модальное окно управления медиафайлами и параметрами будет доступно сразу после сохранения лота.
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="ad-btn ad-btn--outline" data-bs-dismiss="modal">
                            <span class="icon-mbri-close"></span> Закрыть
                        </button>
                    </div>
                </div>
            </div>
        </div>`;

        $('#cars').append(html_card);
        $('body').append(modal_html);

        $('#no_cars').addClass('d-none');
        showAuctionToast(`Автомобиль ${mark} ${model} добавлен в лот!`, 'Успешно', 'success');

        var offcanvasEl = document.getElementById('offcanvasRight');
        if (offcanvasEl) {
            var offcanvas = bootstrap.Offcanvas.getInstance(offcanvasEl);
            if (offcanvas) offcanvas.hide();
        }

        refresh_board();
    }).fail(function() {
        showAuctionToast('Ошибка соединения при получении данных автомобиля', 'Ошибка', 'danger');
    });
}

function delete_car(slug) {
    if (!confirm('Вы уверены, что хотите удалить этот автомобиль из лота?')) {
        return;
    }

    var cardId = '#cars_list_data_id_' + slug;
    var modalId = '#cars_list_data_slug_' + slug + '_modal';

    $(cardId).remove();
    $(modalId).remove();

    showAuctionToast('Автомобиль удален из лота', 'Информация', 'info');
    refresh_board();
}

/* ==========================================================================
   OFFCANVAS DATA FETCHER
   ========================================================================== */
function visible_canvas() {
    var offcanvasElement = document.getElementById('offcanvasRight');
    if (offcanvasElement) {
        var offcanvas = bootstrap.Offcanvas.getOrCreateInstance(offcanvasElement);
        offcanvas.show();
    }
}

function visible_loader(visible) {
    if (visible) {
        $('#load_gif').removeClass('d-none');
    } else {
        $('#load_gif').addClass('d-none');
    }

    if (scroll_data) {
        $('#more').removeClass('d-none');
    } else {
        $('#more').addClass('d-none');
    }
}

function refresh_data_online() {
    var search = $('#search').val() || '';
    var url = '/auction/js/get_cars_lot_online/?store_id=' + store_id + '&search=' + encodeURIComponent(search) + '&page=' + page;

    $.get(url, function(data) {
        if (!Array.isArray(data)) {
            data = [];
        }

        if (data.length === 0) {
            scroll_data = false;
        } else {
            scroll_data = true;
        }

        var html = '';
        var fmt = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 });

        for (var s = 0; s < data.length; s++) {
            var obj = data[s];
            var id = obj.slug;
            var mark = obj.mark_name || '';
            var model = obj.model_name || '';
            var mod = obj.modification_name || '';
            var car_run = fmt.format(obj.run || 0);
            var car_price = fmt.format(obj.price || 0);
            var photo = (obj.url && obj.url.length) ? (Array.isArray(obj.url) ? obj.url[0] : obj.url) : '/media/nophoto.png';

            html += `
            <div id="cars-list_data_${id}" class="ad-drawer-card">
                <div class="ad-drawer-card__thumb">
                    <img src="${photo}" alt="${mark} ${model}">
                </div>
                <div class="ad-drawer-card__info">
                    <div class="ad-drawer-card__title">${mark} ${model}</div>
                    <div class="text-muted small">${mod}</div>
                    <div class="text-muted small">${obj.year} г. • ${car_run} км</div>
                    <div class="ad-drawer-card__price">${car_price} ₽</div>
                </div>
                <div class="ad-drawer-card__actions">
                    <button type="button" class="ad-drawer-icon-btn" onclick="subbmit_car('${id}')" title="Добавить в лот">
                        <span class="icon-mbri-plus"></span>
                    </button>
                    <button type="button" class="ad-drawer-icon-btn" onclick="info_car('${id}')" title="Детальный просмотр">
                        <span class="icon-mbri-preview"></span>
                    </button>
                </div>
            </div>`;
        }

        if (page === 0 && data.length === 0) {
            html = '<div class="text-center text-muted py-4">Автомобили не найдены</div>';
        }

        var container = document.querySelector('#cars-list');
        if (container) {
            container.innerHTML = (page === 0 ? html : container.innerHTML + html);
        }

        visible_loader(false);
    }).fail(function() {
        visible_loader(false);
        showAuctionToast('Ошибка при загрузке автомобилей со стоянки', 'Ошибка', 'danger');
    });
}

/* ==========================================================================
   CAR QUICK INSPECTION PREVIEW MODAL (OFFCANVAS ITEM PREVIEW)
   ========================================================================== */
function info_car(slug) {
    $('#rlk').modal('show');
    var url = '/auction/js/get_cars_lot_online/' + slug + '/';

    $.get(url, function(data) {
        if (!Array.isArray(data)) {
            data = data ? [data] : [];
        }
        if (!data.length) return;

        var obj = data[0];
        var mark = obj.mark_name || '';
        var model = obj.model_name || '';
        var mod = obj.modification_name || '';
        var fmt = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 });

        var car_run = fmt.format(obj.run || 0);
        var car_price = fmt.format(obj.price || 0);
        var car_outlay = fmt.format(obj.outlay || 0);
        var car_bcp = fmt.format(obj.bcp || 0);
        var car_cost_price = fmt.format(obj.cost_price || 0);

        $('#info_car_name').html(`${mark} ${model} ${mod} • ${obj.year} г. • VIN: ${obj.vin || '-'}`);
        $('#info_car_type_sale').text('Тип продажи: ' + (obj.type_sale_name || '-'));
        $('#info_car_type_reception').text('Тип приема: ' + (obj.type_reception_name || '-'));

        $('#info_car_run_value').text(car_run + ' км');
        $('#info_car_modification_value').text(mod || '-');
        $('#info_car_days_in_stok_value').text((obj.days_in_stok || 0) + ' д.');
        $('#info_car_status_name_value').text(obj.status_name || '-');
        $('#info_car_price_value').text(car_price + ' ₽');
        $('#info_car_stage_price_value').text(obj.stage_price_name || '-');
        $('#info_car_cost_price_value').text(car_cost_price + ' ₽');
        $('#info_car_bcp_value').text(car_bcp + ' ₽');
        $('#info_car_outlay_value').text(car_outlay + ' ₽');

        $('#info_car_description_podgotovka').val(obj.description_podgotovka || '');
        $('#info_car_description_op').val(obj.description_op || '');
        $('#info_car_comment_diagnostica').val(obj.int_ocenka_diagnostika || '');

        // Works text
        var worksText = '';
        if (obj.work_podgotovka && obj.work_podgotovka.length) {
            for (var w = 0; w < obj.work_podgotovka.length; w++) {
                worksText += obj.work_podgotovka[w].name + '\n';
            }
        }
        $('#work_car').val(worksText);

        // General Photos
        var photoHtml = '';
        if (obj.url && obj.url.length) {
            for (var p = 0; p < obj.url.length; p++) {
                photoHtml += `
                <div class="ad-photo-tile">
                    <div class="ad-photo-tile__img-wrap">
                        <img src="${obj.url[p]}" alt="Фото ${p+1}">
                    </div>
                </div>`;
            }
        }
        var photoContainer = document.querySelector('#info_car_photos');
        if (photoContainer) photoContainer.innerHTML = photoHtml;

        // Scheme Body Photos
        var schemeHtml = '';
        var schemeArr = [
            obj.int_ocenka_url_pered,
            obj.int_ocenka_url_right,
            obj.int_ocenka_url_zad,
            obj.int_ocenka_url_left,
            obj.int_ocenka_url_up,
            obj.int_ocenka_url_salon
        ];
        for (var sc = 0; sc < schemeArr.length; sc++) {
            if (schemeArr[sc]) {
                schemeHtml += `
                <div class="ad-photo-tile">
                    <div class="ad-photo-tile__img-wrap">
                        <img src="${schemeArr[sc]}" alt="Схема ${sc+1}">
                    </div>
                </div>`;
            }
        }
        var schemeContainer = document.querySelector('#info_car_photos_int_body');
        if (schemeContainer) schemeContainer.innerHTML = schemeHtml;

        // Damages Photos
        var damageHtml = '';
        if (obj.int_ocenka_url_damage && obj.int_ocenka_url_damage.length) {
            for (var dm = 0; dm < obj.int_ocenka_url_damage.length; dm++) {
                damageHtml += `
                <div class="ad-photo-tile">
                    <div class="ad-photo-tile__img-wrap">
                        <img src="${obj.int_ocenka_url_damage[dm]}" alt="Повреждение ${dm+1}">
                    </div>
                </div>`;
            }
        }
        var damageContainer = document.querySelector('#info_car_photos_damage');
        if (damageContainer) damageContainer.innerHTML = damageHtml;
    });
}

/* ==========================================================================
   TOAST NOTIFICATION HELPER
   ========================================================================== */
function showAuctionToast(message, title, type) {
    var container = document.getElementById('container_toast');
    if (!container) return;

    var iconClass = 'icon-mbri-info';
    var textClass = 'text-info';

    if (type === 'success') {
        iconClass = 'icon-mbri-success';
        textClass = 'text-success';
    } else if (type === 'warning') {
        iconClass = 'icon-mbri-alert';
        textClass = 'text-warning';
    } else if (type === 'danger') {
        iconClass = 'icon-mbri-close';
        textClass = 'text-danger';
    }

    var toastId = 'toast_' + Date.now();
    var toastHtml = `
    <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true" data-bs-delay="4000" data-bs-autohide="true">
        <div class="toast-header">
            <span class="${iconClass} me-2 ${textClass}"></span>
            <strong class="me-auto">${title || 'Аукцион'}</strong>
            <small class="text-muted">сейчас</small>
            <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Закрыть"></button>
        </div>
        <div class="toast-body">
            ${message}
        </div>
    </div>`;

    container.insertAdjacentHTML('beforeend', toastHtml);
    var toastEl = document.getElementById(toastId);
    if (toastEl) {
        var toastInstance = new bootstrap.Toast(toastEl);
        toastInstance.show();
        toastEl.addEventListener('hidden.bs.toast', function() {
            toastEl.remove();
        });
    }
}

/* ==========================================================================
   CUSTOM STORE SEARCHABLE COMBOBOX (.af-combo)
   ========================================================================== */
function initStoreCombo() {
    var $combo = $('#ad_store_combo');
    if (!$combo.length) return;

    var $btn = $combo.find('.af-combo__btn');
    var $panel = $combo.find('.af-combo__panel');
    var $search = $combo.find('.af-combo__search');
    var $list = $combo.find('.af-combo__list');
    var $label = $('#ad_store_label');
    var $select = $('select#store');

    // Toggle dropdown
    $btn.on('click', function(e) {
        e.stopPropagation();
        var isOpen = $combo.hasClass('is-open');
        // Close calendar if open
        $('#ad_dt_picker').removeClass('is-open');
        $('#ad_cal_popup').attr('hidden', true);

        if (isOpen) {
            $combo.removeClass('is-open');
            $panel.attr('hidden', true);
            $btn.attr('aria-expanded', 'false');
        } else {
            $combo.addClass('is-open');
            $panel.removeAttr('hidden');
            $btn.attr('aria-expanded', 'true');
            $search.val('').trigger('input');
            setTimeout(function() {
                $search.focus();
            }, 50);
        }
    });

    // Search filter
    $search.on('input', function(e) {
        var query = ($(this).val() || '').toLowerCase().trim();
        $list.find('.af-combo__option').each(function() {
            var text = ($(this).data('label') || $(this).text() || '').toLowerCase();
            if (!query || text.indexOf(query) !== -1) {
                $(this).removeClass('d-none');
            } else {
                $(this).addClass('d-none');
            }
        });
    });

    // Option selection
    $list.on('click', '.af-combo__option', function(e) {
        e.stopPropagation();
        var val = $(this).data('value') !== undefined ? String($(this).data('value')) : '';
        var label = $(this).data('label') || $(this).text().trim();

        $list.find('.af-combo__option').removeClass('is-active').attr('aria-selected', 'false');
        $(this).addClass('is-active').attr('aria-selected', 'true');

        $label.text(label);
        $select.val(val).trigger('change');

        $combo.removeClass('is-open');
        $panel.attr('hidden', true);
        $btn.attr('aria-expanded', 'false');
    });

    // Prevent panel clicks from bubbling
    $panel.on('click', function(e) {
        e.stopPropagation();
    });

    // Close on outside click
    $(document).on('click', function(e) {
        if (!$(e.target).closest('#ad_store_combo').length) {
            $combo.removeClass('is-open');
            $panel.attr('hidden', true);
            $btn.attr('aria-expanded', 'false');
        }
    });

    // Close on Esc
    $(document).on('keydown', function(e) {
        if (e.key === 'Escape' && $combo.hasClass('is-open')) {
            $combo.removeClass('is-open');
            $panel.attr('hidden', true);
            $btn.attr('aria-expanded', 'false');
            $btn.focus();
        }
    });
}

/* ==========================================================================
   CUSTOM DATE & TIME PICKER POPUP (.ad-dt-picker & .af-cal)
   ========================================================================== */
function initDateTimePicker() {
    var $picker = $('#ad_dt_picker');
    if (!$picker.length) return;

    var $trigger = $('#ad_dt_trigger');
    var $popup = $('#ad_cal_popup');
    var $hiddenInput = $('#dateStart');
    var $text = $('#ad_dt_text');
    var $timeBadge = $('#ad_dt_time_badge');
    var $grid = $('#ad_cal_grid');
    var $title = $('#ad_cal_title');
    var $hourSelect = $('#ad_cal_hour');
    var $minSelect = $('#ad_cal_minute');

    var monthNames = [
        'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
        'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
    ];

    // Populate hour options (00-23)
    var hourHtml = '';
    for (var h = 0; h < 24; h++) {
        var hStr = (h < 10 ? '0' : '') + h;
        hourHtml += '<option value="' + hStr + '">' + hStr + '</option>';
    }
    $hourSelect.html(hourHtml);

    // Populate minute options (00, 05, 10 ... 55)
    var minHtml = '';
    for (var m = 0; m < 60; m += 5) {
        var mStr = (m < 10 ? '0' : '') + m;
        minHtml += '<option value="' + mStr + '">' + mStr + '</option>';
    }
    $minSelect.html(minHtml);

    // Parse initial date from hidden input
    var initialVal = ($hiddenInput.val() || '').trim();
    var curDate = new Date();
    if (initialVal) {
        var parsed = new Date(initialVal);
        if (!isNaN(parsed.getTime())) {
            curDate = parsed;
        }
    }

    var selectedYear = curDate.getFullYear();
    var selectedMonth = curDate.getMonth();
    var selectedDay = curDate.getDate();
    var selectedHour = (curDate.getHours() < 10 ? '0' : '') + curDate.getHours();
    var roundedMin = Math.round(curDate.getMinutes() / 5) * 5;
    if (roundedMin >= 60) roundedMin = 55;
    var selectedMin = (roundedMin < 10 ? '0' : '') + roundedMin;

    $hourSelect.val(selectedHour);
    $minSelect.val(selectedMin);

    var viewYear = selectedYear;
    var viewMonth = selectedMonth;

    function renderGrid() {
        $title.text(monthNames[viewMonth] + ' ' + viewYear);
        var today = new Date();
        var todayY = today.getFullYear();
        var todayM = today.getMonth();
        var todayD = today.getDate();

        // Find day of week for 1st day of month (0 = Sun, 1 = Mon ... 6 = Sat)
        var firstDayIdx = new Date(viewYear, viewMonth, 1).getDay();
        var startOffset = (firstDayIdx === 0 ? 6 : firstDayIdx - 1);

        var daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();
        var daysInPrevMonth = new Date(viewYear, viewMonth, 0).getDate();

        var html = '';

        // Previous month days
        for (var p = startOffset - 1; p >= 0; p--) {
            var prevD = daysInPrevMonth - p;
            html += '<button type="button" class="af-cal__day is-mute" data-dir="-1" data-day="' + prevD + '">' + prevD + '</button>';
        }

        // Current month days
        for (var d = 1; d <= daysInMonth; d++) {
            var isToday = (todayY === viewYear && todayM === viewMonth && todayD === d);
            var isPick = (selectedYear === viewYear && selectedMonth === viewMonth && selectedDay === d);
            var cls = 'af-cal__day';
            if (isToday) cls += ' is-today';
            if (isPick) cls += ' is-pick';
            html += '<button type="button" class="' + cls + '" data-day="' + d + '">' + d + '</button>';
        }

        // Next month filler
        var totalCells = startOffset + daysInMonth;
        var nextDays = (totalCells % 7 === 0) ? 0 : 7 - (totalCells % 7);
        if (totalCells + nextDays < 42) {
            nextDays += (42 - (totalCells + nextDays));
        }
        for (var n = 1; n <= nextDays; n++) {
            html += '<button type="button" class="af-cal__day is-mute" data-dir="1" data-day="' + n + '">' + n + '</button>';
        }

        $grid.html(html);
    }

    renderGrid();

    // Toggle Calendar Popup
    $trigger.on('click', function(e) {
        e.stopPropagation();
        var isOpen = $picker.hasClass('is-open');
        // Close store combo if open
        $('#ad_store_combo').removeClass('is-open');
        $('#ad_store_combo .af-combo__panel').attr('hidden', true);

        if (isOpen) {
            $picker.removeClass('is-open');
            $popup.attr('hidden', true);
            $trigger.attr('aria-expanded', 'false');
        } else {
            $picker.addClass('is-open');
            $popup.removeAttr('hidden');
            $trigger.attr('aria-expanded', 'true');
            viewYear = selectedYear;
            viewMonth = selectedMonth;
            renderGrid();
        }
    });

    // Prev / Next month buttons
    $('#ad_cal_prev').on('click', function(e) {
        e.stopPropagation();
        viewMonth--;
        if (viewMonth < 0) {
            viewMonth = 11;
            viewYear--;
        }
        renderGrid();
    });

    $('#ad_cal_next').on('click', function(e) {
        e.stopPropagation();
        viewMonth++;
        if (viewMonth > 11) {
            viewMonth = 0;
            viewYear++;
        }
        renderGrid();
    });

    // Day Click
    $grid.on('click', '.af-cal__day', function(e) {
        e.stopPropagation();
        var day = parseInt($(this).data('day'), 10);
        var dir = $(this).data('dir');

        if (dir === -1) {
            viewMonth--;
            if (viewMonth < 0) {
                viewMonth = 11;
                viewYear--;
            }
        } else if (dir === 1) {
            viewMonth++;
            if (viewMonth > 11) {
                viewMonth = 0;
                viewYear++;
            }
        }

        selectedYear = viewYear;
        selectedMonth = viewMonth;
        selectedDay = day;
        renderGrid();
    });

    // Time Presets
    $popup.on('click', '.ad-cal-preset-btn', function(e) {
        e.stopPropagation();
        var timeStr = $(this).data('time');
        if (timeStr) {
            var parts = timeStr.split(':');
            $hourSelect.val(parts[0]);
            $minSelect.val(parts[1]);
            $popup.find('.ad-cal-preset-btn').removeClass('is-active');
            $(this).addClass('is-active');
        }
    });

    // Today Button
    $('#ad_cal_today_btn').on('click', function(e) {
        e.stopPropagation();
        var now = new Date();
        selectedYear = now.getFullYear();
        selectedMonth = now.getMonth();
        selectedDay = now.getDate();
        viewYear = selectedYear;
        viewMonth = selectedMonth;
        renderGrid();
    });

    // Apply Button
    $('#ad_cal_apply_btn').on('click', function(e) {
        e.stopPropagation();
        var hVal = $hourSelect.val();
        var mVal = $minSelect.val();

        var padM = (selectedMonth + 1 < 10 ? '0' : '') + (selectedMonth + 1);
        var padD = (selectedDay < 10 ? '0' : '') + selectedDay;

        // Standard Django format: YYYY-MM-DDTHH:MM
        var isoVal = selectedYear + '-' + padM + '-' + padD + 'T' + hVal + ':' + mVal;
        var displayStr = padD + '.' + padM + '.' + selectedYear + ', ' + hVal + ':' + mVal;

        $hiddenInput.val(isoVal).trigger('change');
        $text.text(displayStr);
        if ($timeBadge.length) {
            $timeBadge.text(hVal + ':' + mVal + ' МСК');
        }

        $picker.removeClass('is-open');
        $popup.attr('hidden', true);
        $trigger.attr('aria-expanded', 'false');
    });

    // Prevent clicks inside popup from bubbling
    $popup.on('click', function(e) {
        e.stopPropagation();
    });

    // Close on outside click
    $(document).on('click', function(e) {
        if (!$(e.target).closest('#ad_dt_picker').length) {
            $picker.removeClass('is-open');
            $popup.attr('hidden', true);
            $trigger.attr('aria-expanded', 'false');
        }
    });

    // Close on Esc
    $(document).on('keydown', function(e) {
        if (e.key === 'Escape' && $picker.hasClass('is-open')) {
            $picker.removeClass('is-open');
            $popup.attr('hidden', true);
            $trigger.attr('aria-expanded', 'false');
            $trigger.focus();
        }
    });
}

/* ==========================================================================
   AUCTION BIDS HISTORY
   ========================================================================== */
function initAuctionBids() {
    var $card = $('#ad_bids_card');
    if (!$card.length) return;

    var uid = $card.data('uid');
    if (!uid) return;

    var numFormatter = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 });

    function formatBidDate(dateStr) {
        if (!dateStr) return '—';
        if (typeof dateStr !== 'string') return String(dateStr);
        if (/^\d{2}\.\d{2}\.\d{4}\s\d{2}:\d{2}/.test(dateStr)) {
            return dateStr;
        }
        try {
            var d = new Date(dateStr);
            if (isNaN(d.getTime())) return dateStr;
            var day = String(d.getDate()).padStart(2, '0');
            var month = String(d.getMonth() + 1).padStart(2, '0');
            var year = d.getFullYear();
            var hours = String(d.getHours()).padStart(2, '0');
            var minutes = String(d.getMinutes()).padStart(2, '0');
            var seconds = String(d.getSeconds()).padStart(2, '0');
            return day + '.' + month + '.' + year + ' ' + hours + ':' + minutes + ':' + seconds;
        } catch (e) {
            return dateStr;
        }
    }

    function loadAuctionBids(isManual) {
        var $btn = $('#refresh_bids_btn');
        var $icon = $('#refresh_bids_icon');
        var $loading = $('#bids_loading');
        var $empty = $('#bids_empty');
        var $error = $('#bids_error');
        var $tableWrap = $('#bids_table_wrap');
        var $tableBody = $('#bids_table_body');
        var $badge = $('#bids_count_badge');
        var $summary = $('#bids_summary_chip');

        var $winnerCard = $('#ad_winner_bids_card');
        var $winnerTableBody = $('#winner_bids_table_body');
        var $winnerBidsBadge = $('#winner_bids_count_badge');

        $icon.addClass('spin');
        $btn.prop('disabled', true);

        if (!isManual && !$tableBody.children().length) {
            $loading.removeClass('d-none');
            $empty.addClass('d-none');
            $error.addClass('d-none');
            $tableWrap.addClass('d-none');
        }

        $.ajax({
            url: '/auction/js/get_bids/' + uid + '/',
            type: 'GET',
            dataType: 'json',
            timeout: 15000,
            success: function(resp) {
                $loading.addClass('d-none');

                if (resp && resp.success) {
                    if (resp.pk_auction) {
                        $('#ad_lot_badge_num').text('№ ' + resp.pk_auction);
                        $('#ad_lot_copy_btn').attr('data-copy', resp.pk_auction);
                        $('#ad_breadcrumb_lot').text('Лот № ' + resp.pk_auction);
                        $('#ad_lot_site_link')
                            .attr('href', 'https://auction.kors-group.ru/lots/' + resp.pk_auction + '/')
                            .removeClass('d-none');
                    }

                    // -------------------------------------------------------------
                    // DYNAMIC STATUS BADGE UPDATE
                    // -------------------------------------------------------------
                    if (resp.status) {
                        var statusName = resp.status;
                        var statusClass = 'is-active';
                        if (statusName === 'Завершен' || statusName === 'Завершён') {
                            statusClass = 'is-finished';
                        } else if (statusName === 'Не сыграл') {
                            statusClass = 'is-not-played';
                        } else if (statusName === 'Отклонено' || statusName === 'Отклонен') {
                            statusClass = 'is-rejected';
                        } else if (statusName === 'Новый' || statusName === 'Подготавливается' || statusName === 'Ожидает' || statusName === 'Ожидание') {
                            statusClass = 'is-draft';
                        }
                        $('#ad_lot_status_container').html(`
                            <span class="ad-status-pill ${statusClass}" id="ad_lot_status_pill">
                                <span class="ad-status-dot"></span>
                                <span id="ad_lot_status_text">${escapeHtml(statusName)}</span>
                            </span>
                        `);
                    }

                    // -------------------------------------------------------------
                    // WINNER & PERSONAL BIDS BLOCK HANDLING
                    // -------------------------------------------------------------
                    var profileWinner = resp.profile_winner;
                    var winnerBids = resp.winner_bids || [];
                    var winnerStats = resp.winner_stats || {};
                    var winningBid = resp.winning_bid || (profileWinner ? profileWinner.winning_bid : 0);

                    if (profileWinner && (winnerBids.length > 0 || winningBid > 0)) {
                        $winnerCard.removeClass('d-none');

                        var wName = profileWinner.name || 'Победитель торгов';
                        $('#winner_det_name').text(wName);

                        if (profileWinner.phone) {
                            $('#winner_det_phone').attr('href', 'tel:' + escapeHtml(profileWinner.phone)).find('span:last').text(profileWinner.phone);
                            $('#winner_det_phone_wrap').removeClass('d-none');
                        } else {
                            $('#winner_det_phone_wrap').addClass('d-none');
                        }

                        if (profileWinner.email) {
                            $('#winner_det_email').attr('href', 'mailto:' + escapeHtml(profileWinner.email)).find('span:last').text(profileWinner.email);
                            $('#winner_det_email_wrap').removeClass('d-none');
                        } else {
                            $('#winner_det_email_wrap').addClass('d-none');
                        }

                        if (profileWinner.city) {
                            $('#winner_det_city').find('span:last').text(profileWinner.city);
                            $('#winner_det_city_wrap').removeClass('d-none');
                        } else {
                            $('#winner_det_city_wrap').addClass('d-none');
                        }

                        var totalWbCount = winnerBids.length;
                        $winnerBidsBadge.text(totalWbCount);
                        $('#winner_det_bids_count').text(totalWbCount);

                        var firstBidAmount = winnerStats.first_bid || (winnerBids.length ? winnerBids[winnerBids.length - 1].amount : winningBid);
                        var growthAmount = winnerStats.growth !== undefined ? winnerStats.growth : (winningBid > firstBidAmount ? winningBid - firstBidAmount : 0);

                        $('#winner_det_price').text(numFormatter.format(winningBid) + ' ₽');
                        $('#winner_det_first_bid').text(numFormatter.format(firstBidAmount) + ' ₽');
                        if (growthAmount > 0) {
                            $('#winner_det_growth').text('+' + numFormatter.format(growthAmount) + ' ₽');
                        } else {
                            $('#winner_det_growth').text('0 ₽');
                        }

                        // Also update top winner banner if present
                        var $topWinner = $('#ad_winner_top_card');
                        if ($topWinner.length) {
                            $topWinner.removeClass('d-none');
                            $('#ad_winner_top_name').text(wName);
                            $('#ad_winner_top_price').text(numFormatter.format(winningBid) + ' ₽');
                        }

                        // Render personal bids table for winner
                        if (winnerBids.length > 0) {
                            var sortedChronological = winnerBids.slice().sort(function(a, b) {
                                var timeA = new Date(a.created_at || a.created_at_iso || 0).getTime();
                                var timeB = new Date(b.created_at || b.created_at_iso || 0).getTime();
                                if (timeA && timeB) return timeA - timeB;
                                return (a.amount || 0) - (b.amount || 0);
                            });

                            var bidsWithDelta = sortedChronological.map(function(b, i) {
                                var delta = 0;
                                if (i > 0) {
                                    delta = (b.amount || 0) - (sortedChronological[i - 1].amount || 0);
                                }
                                return {
                                    bid: b,
                                    stepNum: i + 1,
                                    delta: delta,
                                    isFirst: (i === 0)
                                };
                            });

                            var displayList = bidsWithDelta.slice().reverse();
                            var winnerRowsHtml = '';

                            displayList.forEach(function(item) {
                                var b = item.bid;
                                var isWinning = !!b.is_winning || (b.amount === winningBid);
                                var rowClass = isWinning ? ' class="ad-winner-bid-row--top"' : '';

                                var amountFormatted = numFormatter.format(b.amount) + ' ₽';
                                var timeFormatted = formatBidDate(b.created_at || b.created_at_iso);

                                var deltaHtml = '';
                                if (item.isFirst) {
                                    deltaHtml = '<span class="ad-bid-delta ad-bid-delta--start">Старт</span>';
                                } else if (item.delta > 0) {
                                    deltaHtml = '<span class="ad-bid-delta">+' + numFormatter.format(item.delta) + ' ₽</span>';
                                } else {
                                    deltaHtml = '<span class="ad-bid-delta">—</span>';
                                }

                                var sourceDisplay = b.source_display || (b.source === 'auto' ? 'Автоставка' : (b.source === 'api' ? 'API' : 'Сайт'));
                                var sourceHtml = '<span class="ad-bid-source-tag"><span class="icon-mbri-globe"></span> ' + escapeHtml(sourceDisplay) + '</span>';

                                var statusHtml = '';
                                if (isWinning) {
                                    statusHtml = '<span class="ad-bid-status-pill is-winner"><span class="icon-mbri-star"></span> Победная ставка</span>';
                                } else if (item.isFirst) {
                                    statusHtml = '<span class="ad-bid-status-pill is-personal-first">Первая ставка</span>';
                                } else {
                                    statusHtml = '<span class="ad-bid-status-pill is-personal-step"><span class="icon-mbri-arrow-up"></span> Шаг торгов</span>';
                                }

                                winnerRowsHtml += `
                                    <tr${rowClass}>
                                        <td class="text-center ad-bid-num">#${item.stepNum}</td>
                                        <td class="ad-bid-time"><span class="icon-mbri-clock me-1 text-muted"></span>${escapeHtml(timeFormatted)}</td>
                                        <td class="ad-bid-amount">${amountFormatted}</td>
                                        <td>${deltaHtml}</td>
                                        <td>${sourceHtml}</td>
                                        <td class="text-end">${statusHtml}</td>
                                    </tr>
                                `;
                            });

                            $winnerTableBody.html(winnerRowsHtml);
                        } else {
                            $winnerTableBody.html('<tr><td colspan="6" class="text-center py-3 text-muted small">История ставок победителя формируется</td></tr>');
                        }
                    } else {
                        $winnerCard.addClass('d-none');
                    }

                    // -------------------------------------------------------------
                    // GENERAL BIDS TABLE HANDLING
                    // -------------------------------------------------------------
                    var bids = resp.bids || [];
                    var totalBids = resp.total_bids !== undefined ? resp.total_bids : bids.length;
                    $badge.text(totalBids);

                    if (bids.length > 0) {
                        var uniqueBidders = resp.unique_bidders !== undefined ? resp.unique_bidders : 0;
                        var maxBid = resp.max_bid !== undefined ? resp.max_bid : 0;

                        $('#bids_unique_bidders').text(uniqueBidders);
                        $('#bids_max_price').text(numFormatter.format(maxBid) + ' ₽');
                        $summary.removeClass('d-none');

                        var rowsHtml = '';
                        bids.forEach(function(bid, index) {
                            var isWinning = !!bid.is_winning;
                            var isLeading = (index === 0 && !isWinning);
                            var rowClass = isWinning ? ' class="ad-bid-row--winning"' : '';

                            var amountFormatted = numFormatter.format(bid.amount) + ' ₽';
                            var timeStr = formatBidDate(bid.created_at || bid.created_at_iso);

                            var userName = (bid.user && bid.user.name) ? bid.user.name : 'Участник';
                            var userCity = (bid.user && bid.user.city) ? '<div class="ad-bid-user-city"><span class="icon-mbri-pin me-1"></span>' + escapeHtml(bid.user.city) + '</div>' : '';

                            var userPhone = (bid.user && bid.user.phone) ? bid.user.phone : '';
                            var userEmail = (bid.user && bid.user.email) ? bid.user.email : '';

                            var contactsHtml = '<div class="d-flex flex-column gap-1">';
                            if (userPhone) {
                                contactsHtml += '<a href="tel:' + escapeHtml(userPhone) + '" class="ad-bid-contact-link"><span class="icon-mbri-phone"></span> ' + escapeHtml(userPhone) + '</a>';
                            }
                            if (userEmail) {
                                contactsHtml += '<a href="mailto:' + escapeHtml(userEmail) + '" class="ad-bid-contact-link"><span class="icon-mbri-letter"></span> ' + escapeHtml(userEmail) + '</a>';
                            }
                            if (!userPhone && !userEmail) {
                                contactsHtml += '<span class="text-muted small">—</span>';
                            }
                            contactsHtml += '</div>';

                            var sourceDisplay = bid.source_display || (bid.source === 'auto' ? 'Автоставка' : (bid.source === 'api' ? 'API' : 'Сайт'));
                            var sourceHtml = '<span class="ad-bid-source-tag"><span class="icon-mbri-globe"></span> ' + escapeHtml(sourceDisplay) + '</span>';

                            var statusHtml = '';
                            if (isWinning) {
                                statusHtml = '<span class="ad-bid-status-pill is-winner"><span class="icon-mbri-star"></span> Победная</span>';
                            } else if (isLeading) {
                                statusHtml = '<span class="ad-bid-status-pill is-leading"><span class="icon-mbri-up-arrow"></span> Лидирует</span>';
                            } else {
                                statusHtml = '<span class="ad-bid-status-pill is-outbid">Перебита</span>';
                            }

                            rowsHtml += `
                                <tr${rowClass}>
                                    <td class="text-center ad-bid-num">${index + 1}</td>
                                    <td class="ad-bid-time"><span class="icon-mbri-clock me-1 text-muted"></span>${escapeHtml(timeStr)}</td>
                                    <td class="ad-bid-amount">${amountFormatted}</td>
                                    <td>
                                        <div class="ad-bid-user-name">${escapeHtml(userName)}</div>
                                        ${userCity}
                                    </td>
                                    <td>${contactsHtml}</td>
                                    <td>${sourceHtml}</td>
                                    <td class="text-end">${statusHtml}</td>
                                </tr>
                            `;
                        });

                        $tableBody.html(rowsHtml);
                        $tableWrap.removeClass('d-none');
                        $empty.addClass('d-none');
                        $error.addClass('d-none');
                    } else {
                        $badge.text(0);
                        $summary.addClass('d-none');
                        $tableBody.empty();
                        $tableWrap.addClass('d-none');
                        $empty.removeClass('d-none');
                        $error.addClass('d-none');
                    }

                    if (isManual) {
                        showAuctionToast('История ставок успешно обновлена', 'Обновлено', 'success');
                    }
                } else {
                    var errMsg = (resp && resp.error) ? resp.error : 'Не удалось загрузить историю ставок';
                    $('#bids_error_text').text(errMsg);
                    $error.removeClass('d-none');
                    if (isManual) {
                        showAuctionToast(errMsg, 'Ошибка', 'danger');
                    }
                }
            },
            error: function(xhr, statusText) {
                $loading.addClass('d-none');
                var errMsg = 'Ошибка связи с сервером при получении ставок';
                $('#bids_error_text').text(errMsg);
                $error.removeClass('d-none');
                if (isManual) {
                    showAuctionToast(errMsg, 'Ошибка', 'danger');
                }
            },
            complete: function() {
                $icon.removeClass('spin');
                $btn.prop('disabled', false);
            }
        });
    }

    function escapeHtml(text) {
        if (!text) return '';
        return String(text)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    // Auto-load on page ready
    loadAuctionBids(false);

    // Manual refresh click
    $('#refresh_bids_btn').on('click', function(e) {
        e.preventDefault();
        loadAuctionBids(true);
    });
}

