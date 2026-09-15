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
    initPreflightChecklist();

    // Price input real-time calculation
    $('#price_start').on('input change', function() {
        refresh_board();
    });

    // Helper: Apply price to input with flash animation & toast
    function applyStartPrice(val, label) {
        if (val === undefined || val === null || isNaN(val) || val <= 0) {
            showAuctionToast('Сначала добавьте автомобиль в лот, чтобы рассчитать минимальную цену', 'Внимание', 'warning');
            return;
        }
        var rounded = Math.round(val);
        var $input = $('#price_start');
        $input.val(rounded).trigger('input').trigger('change');

        // Trigger flash animation
        $input.removeClass('ad-price-flash');
        if ($input.length && $input[0]) {
            void $input[0].offsetWidth;
        }
        $input.addClass('ad-price-flash');

        var formatted = new Intl.NumberFormat('ru-RU').format(rounded);
        showAuctionToast(label ? (label + ': ' + formatted + ' ₽') : ('Установлена цена: ' + formatted + ' ₽'), 'Стартовая цена', 'success');
    }

    // Min price direct one-click buttons
    $(document).on('click', '#btn_set_min_price, #btn_quick_min_inline, #min_price_chip', function(e) {
        e.preventDefault();
        var minVal = $(this).data('min-val');
        if (minVal === undefined || minVal === null || isNaN(minVal)) {
            minVal = window._current_min_price || parseFloat($('#price_start').attr('min')) || 0;
        }
        applyStartPrice(minVal, 'Установлена минимальная цена');
    });

    // Preset +5% button
    $(document).on('click', '#btn_add_5pct', function(e) {
        e.preventDefault();
        var minVal = window._current_min_price || parseFloat($('#price_start').attr('min')) || 0;
        if (minVal > 0) {
            var target = Math.round((minVal * 1.05) / 1000) * 1000;
            applyStartPrice(target, 'Установлена цена (+5%)');
        } else {
            showAuctionToast('Сначала добавьте автомобиль в лот', 'Внимание', 'warning');
        }
    });

    // Preset +10% button
    $(document).on('click', '#btn_add_10pct', function(e) {
        e.preventDefault();
        var minVal = window._current_min_price || parseFloat($('#price_start').attr('min')) || 0;
        if (minVal > 0) {
            var target = Math.round((minVal * 1.10) / 1000) * 1000;
            applyStartPrice(target, 'Установлена цена (+10%)');
        } else {
            showAuctionToast('Сначала добавьте автомобиль в лот', 'Внимание', 'warning');
        }
    });

    // Preset +50 000 ₽ button
    $(document).on('click', '#btn_round_50k', function(e) {
        e.preventDefault();
        var cur = parseFloat($('#price_start').val()) || window._current_min_price || parseFloat($('#price_start').attr('min')) || 0;
        if (cur > 0) {
            var target = cur + 50000;
            applyStartPrice(target, 'Цена увеличена (+50 000 ₽)');
        } else {
            showAuctionToast('Сначала укажите стартовую цену или добавьте авто', 'Внимание', 'warning');
        }
    });

    // Edit car modal opener
    $(document).on('click', '[id^="edit_car_info_"]', function() {
        var id = this.id.replace('edit_car_info_', '');
        var modalId = 'cars_list_data_slug_' + id + '_modal';
        $('#' + modalId).modal('show');
    });

    // Add cars trigger (opens offcanvas)
    $('#add_cars, #btn_empty_add_car, #step_empty_select').on('click', function() {
        store_id = $('select#store option:selected').val() || $('select#store option:selected').attr('text') || '';

        if (!store_id) {
            showAuctionToast('Пожалуйста, выберите стоянку перед добавлением автомобиля', 'Внимание', 'warning');
            if ($('#wrap_store_combo').length) {
                $('html, body').animate({ scrollTop: $('#wrap_store_combo').offset().top - 100 }, 300);
                setTimeout(function() {
                    if (!$('#ad_store_combo').hasClass('is-open')) {
                        $('#ad_store_combo .af-combo__btn').trigger('click');
                    }
                }, 350);
            } else {
                $('select#store').focus();
            }
            return;
        }

        var carsList = document.querySelector('#cars-list');
        if (carsList) carsList.innerHTML = '';

        page = 0;
        visible_loader(true);
        refresh_data_online();
        visible_canvas();
    });

    // Quick navigation from empty deck onboarding steps
    $('#step_empty_store').on('click', function() {
        if ($('#wrap_store_combo').length) {
            $('html, body').animate({ scrollTop: $('#wrap_store_combo').offset().top - 100 }, 300);
            setTimeout(function() {
                if (!$('#ad_store_combo').hasClass('is-open')) {
                    $('#ad_store_combo .af-combo__btn').trigger('click');
                }
            }, 350);
        }
    });

    $('#step_empty_price').on('click', function() {
        if ($('#price_start').length) {
            $('html, body').animate({ scrollTop: $('#price_start').offset().top - 120 }, 300);
            setTimeout(function() {
                $('#price_start').focus();
            }, 350);
        }
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
        var query = ($(this).val() || '').trim();
        if (query.length > 0) {
            $('#ad_search_clear').removeClass('d-none');
        } else {
            $('#ad_search_clear').addClass('d-none');
        }

        clearTimeout(searchTimer);
        searchTimer = setTimeout(function() {
            page = 0;
            var carsList = document.querySelector('#cars-list');
            if (carsList) carsList.innerHTML = '';
            visible_loader(true);
            refresh_data_online();
        }, 320);
    });

    $('#ad_search_clear').on('click', function() {
        $('#search').val('').trigger('input').focus();
    });

    // Enter in search triggers immediate search
    $('#search').on('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            clearTimeout(searchTimer);
            page = 0;
            var carsList = document.querySelector('#cars-list');
            if (carsList) carsList.innerHTML = '';
            visible_loader(true);
            refresh_data_online();
        }
    });

    // Quick client filter chips: "Все" / "Свободные"
    $(document).on('click', '.ad-drawer-chip-btn', function() {
        $('.ad-drawer-chip-btn').removeClass('active');
        $(this).addClass('active');
        var filter = $(this).data('filter');
        if (filter === 'available') {
            $('#cars-list .ad-drawer-card.is-in-lot').slideUp(180);
        } else {
            $('#cars-list .ad-drawer-card').slideDown(180);
        }
    });

    // Offcanvas events
    var offcanvasEl = document.getElementById('offcanvasRight');
    if (offcanvasEl) {
        offcanvasEl.addEventListener('hide.bs.offcanvas', function() {
            $('#cars-list').addClass('fade-out');
        });
        offcanvasEl.addEventListener('hidden.bs.offcanvas', function() {
            $('#cars-list').empty().removeClass('fade-out');
            $('#search').val('');
            $('#ad_search_clear').addClass('d-none');
            $('.ad-drawer-chip-btn').removeClass('active');
            $('#btn_filter_all').addClass('active');
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
    $(document).on('click', '.ad-tab-btn, .ad-modal-tab-btn', function() {
        var $btn = $(this);
        var targetId = $btn.data('target');
        if (!targetId) return;
        var $modal = $btn.closest('.modal');

        $modal.find('.ad-tab-btn, .ad-modal-tab-btn').removeClass('active');
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

    // Start Price minimum enforcement & quick button updates
    window._current_min_price = price_cars;
    $('#price_start').attr('min', price_cars);
    $('#btn_set_min_price').data('min-val', price_cars);
    $('#btn_quick_min_inline').data('min-val', price_cars);

    if (price_cars > 0) {
        $('#btn_set_min_price_val').text(price_cars_str + ' ₽');
        $('#btn_set_min_price, #btn_add_5pct, #btn_add_10pct, #btn_round_50k, #btn_quick_min_inline')
            .prop('disabled', false)
            .removeClass('is-disabled');

        var p5 = Math.round((price_cars * 1.05) / 1000) * 1000;
        var p10 = Math.round((price_cars * 1.10) / 1000) * 1000;
        $('#btn_add_5pct').attr('title', '+5% к мин. цене: ' + formatter.format(p5) + ' ₽');
        $('#btn_add_10pct').attr('title', '+10% к мин. цене: ' + formatter.format(p10) + ' ₽');

        // Active state if currently equals min price
        if (price_lot === price_cars) {
            $('#btn_set_min_price, #btn_quick_min_inline').addClass('is-active');
        } else {
            $('#btn_set_min_price, #btn_quick_min_inline').removeClass('is-active');
        }

        // Active state for +5% or +10%
        if (price_lot === p5) {
            $('#btn_add_5pct').addClass('is-active');
        } else {
            $('#btn_add_5pct').removeClass('is-active');
        }
        if (price_lot === p10) {
            $('#btn_add_10pct').addClass('is-active');
        } else {
            $('#btn_add_10pct').removeClass('is-active');
        }

        // Price status badge
        var $priceBadge = $('#price_status_badge');
        if (price_lot > 0) {
            if (price_lot >= price_cars) {
                $priceBadge.removeClass('is-invalid').addClass('is-valid').html('✓ Мин. цена соблюдена').show();
            } else {
                $priceBadge.removeClass('is-valid').addClass('is-invalid').html('⚠️ Ниже мин. цены (' + price_cars_str + ' ₽)').show();
            }
        } else {
            $priceBadge.hide();
        }

        $('#min_price_start').html('Мин. стартовая цена: <span class="ad-min-price-chip" id="min_price_chip" data-min-val="' + price_cars + '" title="Нажмите для применения">' + price_cars_str + ' ₽</span> <span class="text-muted small ms-1">(сумма цен авто)</span>');
    } else {
        $('#btn_set_min_price_val').text('—');
        $('#btn_set_min_price, #btn_add_5pct, #btn_add_10pct, #btn_round_50k, #btn_quick_min_inline')
            .prop('disabled', true)
            .addClass('is-disabled')
            .removeClass('is-active');
        $('#price_status_badge').hide();
        $('#min_price_start').html('<span>Мин. цена рассчитывается автоматически на основе авто в лоте</span>');
    }

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

    checkPreflight();
}

/* ==========================================================================
   PRE-FLIGHT CHECKLIST (Готовность лота к торгам)
   ========================================================================== */
function initPreflightChecklist() {
    var $preflight = $('#ad_preflight');
    if (!$preflight.length) return;

    // Listen to changes on relevant fields
    $('#dateStart').on('change input', function() {
        checkPreflight();
    });

    $('#price_start').on('input change keyup', function() {
        checkPreflight();
    });

    $(document).on('change', 'input[type="checkbox"][id*="_photo_"]', function() {
        checkPreflight();
    });

    $(document).on('change', 'input[type="file"][id*="images_"]', function() {
        checkPreflight();
    });

    // Item click navigation for interactive quick fix
    $('#preflight_car').on('click', function() {
        if ($('#add_cars').length && $('#add_cars').is(':visible')) {
            $('#add_cars').trigger('click');
        } else if ($('#no_cars button').length && $('#no_cars button').is(':visible')) {
            $('#no_cars button').trigger('click');
        } else if ($('#cars').length) {
            $('html, body').animate({ scrollTop: $('#cars').offset().top - 90 }, 350);
        }
    });

    $('#preflight_photos').on('click', function() {
        var $editBtn = $('.ad-car-actions-row button[id*="edit_car_info_"]').first();
        if ($editBtn.length) {
            $editBtn.trigger('click');
            setTimeout(function() {
                $('.ad-tab-btn[data-target*="tab_gallery_"]').first().trigger('click');
            }, 250);
        } else if ($('#cars').length) {
            $('html, body').animate({ scrollTop: $('#cars').offset().top - 90 }, 350);
        }
    });

    $('#preflight_price').on('click', function() {
        if ($('#price_start').length) {
            $('html, body').animate({ scrollTop: $('#price_start').offset().top - 140 }, 350, function() {
                $('#price_start').focus().select();
            });
        }
    });

    $('#preflight_start').on('click', function() {
        if ($('#ad_dt_trigger').length) {
            $('html, body').animate({ scrollTop: $('#ad_dt_trigger').offset().top - 140 }, 350, function() {
                $('#ad_dt_trigger').trigger('click');
            });
        }
    });

    // Intercept submit on "На торги" button if not ready
    $(document).on('click', '#send', function(e) {
        if ($(this).hasClass('is-unready')) {
            e.preventDefault();
            e.stopPropagation();

            var $widget = $('#ad_preflight');
            $widget.removeClass('ad-preflight--shake');
            // Force reflow
            if ($widget.length && $widget[0]) {
                void $widget[0].offsetWidth;
            }
            $widget.addClass('ad-preflight--shake');

            showAuctionToast('Заполните все 4 пункта чек-листа готовности перед отправкой лота на торги!', 'Внимание', 'warning');
            return false;
        }
    });

    checkPreflight();
}

function checkPreflight() {
    var $preflight = $('#ad_preflight');
    if (!$preflight.length) return;

    var carCards = $('[id*="cars_list_data_id_"]');
    var carCount = carCards.length;
    var hasCar = carCount > 0;

    // Photos check
    var hasPhotos = false;
    if (hasCar) {
        carCards.each(function() {
            var $thumb = $(this).find('.ad-car-thumb img');
            if ($thumb.length && $thumb.attr('src') && $thumb.attr('src').indexOf('nophoto') === -1 && $thumb.css('display') !== 'none') {
                hasPhotos = true;
            }
            var slug = this.id.replace('cars_list_data_id_', '');
            var $modal = $('#cars_list_data_slug_' + slug + '_modal');
            if ($modal.length) {
                if ($modal.find('.ad-photo-tile').length > 0) {
                    hasPhotos = true;
                }
                if ($modal.find('input[type="checkbox"][name*="_photo_"]:checked').length > 0) {
                    hasPhotos = true;
                }
            }
        });
    }

    // Price check
    var priceStart = parseFloat($('#price_start').val()) || 0;
    var minPrice = parseFloat($('#price_start').attr('min')) || 0;
    var hasPrice = priceStart > 0 && (minPrice === 0 || priceStart >= minPrice);

    // Date start check
    var dateStartVal = ($('#dateStart').val() || '').trim();
    var hasDateStart = dateStartVal.length > 0;

    // Formatted date string for start
    var dateDisplay = 'Не назначен';
    if (hasDateStart) {
        var dtText = $('#ad_dt_text').text().trim();
        if (dtText && dtText.indexOf('Выберите') === -1) {
            dateDisplay = dtText;
        } else {
            dateDisplay = 'Назначен';
        }
    }

    var priceDisplay = hasPrice ? (new Intl.NumberFormat('ru-RU').format(priceStart) + ' ₽') : 'Не указана';
    var carDisplay = hasCar ? (carCount === 1 ? '1 авто в лоте' : carCount + ' авто в лоте') : 'Не прикреплён';
    var photosDisplay = hasPhotos ? 'Загружены' : 'Не загружены';

    var items = [
        {
            $el: $('#preflight_car'),
            $val: $('#preflight_car_val'),
            valText: carDisplay,
            ok: hasCar
        },
        {
            $el: $('#preflight_photos'),
            $val: $('#preflight_photos_val'),
            valText: photosDisplay,
            ok: hasPhotos
        },
        {
            $el: $('#preflight_price'),
            $val: $('#preflight_price_val'),
            valText: priceDisplay,
            ok: hasPrice
        },
        {
            $el: $('#preflight_start'),
            $val: $('#preflight_start_val'),
            valText: dateDisplay,
            ok: hasDateStart
        }
    ];

    var score = 0;
    items.forEach(function(item) {
        if (!item.$el.length) return;
        if (item.ok) {
            score++;
            item.$el.removeClass('is-pending').addClass('is-ok');
            item.$el.find('.ad-chk-tile__tag, .ad-pod__status-txt, .ad-pod__status').text('Готово');
        } else {
            item.$el.removeClass('is-ok').addClass('is-pending');
            item.$el.find('.ad-chk-tile__tag, .ad-pod__status-txt, .ad-pod__status').text('Требуется');
        }
        if (item.$val && item.$val.length) {
            item.$val.text(item.valText);
        }
    });

    var pct = Math.round((score / 4) * 100);
    var $score = $('#preflight_score');
    var $progress = $('#preflight_progress');
    var $gaugeVal = $('#preflight_gauge_val');

    // Update progress track fill
    if ($progress.length) {
        $progress.css('width', pct + '%');
    }

    // Update circular SVG gauge if present
    if ($gaugeVal.length) {
        $gaugeVal.attr('stroke-dasharray', pct + ', 100');
    }

    if ($score.length) {
        $score.text(score === 4 ? '4 из 4 • Готов' : score + ' из 4');
    }

    if (score === 4) {
        $preflight.removeClass('is-incomplete').addClass('is-ready');
    } else {
        $preflight.removeClass('is-ready').addClass('is-incomplete');
    }

    // "На торги" Button Highlight & state
    var $sendBtn = $('#send');
    if ($sendBtn.length) {
        if (score === 4) {
            $sendBtn.removeClass('is-unready').addClass('is-ready');
            $sendBtn.attr('title', 'Все пункты выполнены! Нажмите для отправки лота на торги');
        } else {
            $sendBtn.removeClass('is-ready').addClass('is-unready');
            $sendBtn.attr('title', 'Выполните все 4 пункта чек-листа готовности для отправки на торги (' + score + '/4)');
        }
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
        var photo0 = (obj.url && obj.url.length && obj.url[0] !== '/media/nophoto.png') ? obj.url[0] : '';

        var fmt = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 });
        var car_run = fmt.format(obj.run || 0);
        var car_price = fmt.format(obj.price || 0);
        var car_cost = fmt.format(obj.cost_price || 0);
        var car_outlay = fmt.format(obj.outlay || 0);
        var car_bcp = fmt.format(obj.bcp || 0);

        var html_card = `
        <div class="ad-car-card" id="cars_list_data_id_${id}" name="cars_list_data_id_${id}">
            <div class="ad-car-showcase">
                <div class="ad-car-thumb" title="Нажмите для увеличения фото">
                    ${photo0 ? `
                        <img src="${photo0}" alt="${mark} ${model}" onerror="this.style.display='none'; if(this.nextElementSibling){this.nextElementSibling.style.display='flex';}">
                        <div class="ad-car-thumb__placeholder" style="display: none;">
                            <span class="icon-truck"></span>
                            <span>Фото отсутствует</span>
                        </div>
                    ` : `
                        <div class="ad-car-thumb__placeholder">
                            <span class="icon-truck"></span>
                            <span>Фото отсутствует</span>
                        </div>
                    `}
                </div>

                <div class="ad-car-details">
                    <div>
                        <h3 class="ad-car-title">${mark} ${model}</h3>
                        <div class="ad-car-modification">${mod}</div>
                    </div>

                    <div class="ad-car-chips">
                        <span class="ad-car-chip"><span class="icon-mbri-calendar me-1"></span>${obj.year} г.в.</span>
                        <span class="ad-car-chip ad-car-chip--mono"><span class="icon-mbri-speed me-1"></span>${car_run} км</span>
                        <span class="ad-car-chip ad-car-chip--mono">
                            VIN: ${obj.vin || '-'}
                            ${obj.vin ? `
                                <button type="button" class="ad-copy-btn ms-1" data-copy="${obj.vin}" title="Скопировать VIN">
                                    <span class="icon-mbri-file"></span>
                                </button>
                            ` : ''}
                        </span>
                    </div>

                    <div class="ad-car-links">
                        <span class="ad-status-pill is-draft">
                            <span class="ad-status-dot"></span> Требует сохранения
                        </span>
                        <a class="ad-car-ext-btn" href="/cars/${id}/" target="_blank" rel="noopener">
                            <span class="icon-mbri-preview"></span> Карточка авто
                        </a>
                        ${obj.rlk_id ? `
                            <a class="ad-car-ext-btn" href="/eco/${obj.rlk_id}/" target="_blank" rel="noopener">
                                <span class="icon-mbri-search"></span> Интерактивная оценка
                            </a>
                        ` : ''}
                    </div>
                </div>

                <div class="ad-car-sidebar">
                    <div class="ad-car-finance-card">
                        <div class="ad-car-finance-grid">
                            <div class="ad-car-finance-cell">
                                <span class="ad-car-finance-cell__label">Себестоимость</span>
                                <span class="ad-car-finance-cell__val">${car_cost} ₽</span>
                            </div>
                            <div class="ad-car-finance-cell">
                                <span class="ad-car-finance-cell__label">Затраты</span>
                                <span class="ad-car-finance-cell__val">${car_outlay} ₽</span>
                            </div>
                            <div class="ad-car-finance-cell">
                                <span class="ad-car-finance-cell__label">БЦП</span>
                                <span class="ad-car-finance-cell__val">${car_bcp} ₽</span>
                            </div>
                            <div class="ad-car-finance-cell ad-car-finance-cell--sale">
                                <span class="ad-car-finance-cell__label">Продажа</span>
                                <span class="ad-car-finance-cell__val">${car_price} ₽</span>
                            </div>
                        </div>
                    </div>

                    <div class="ad-car-actions-row">
                        <button type="button" class="ad-btn ad-btn--primary w-100" id="edit_car_info_${id}">
                            <span class="icon-mbri-setting2"></span> Настроить автомобиль
                        </button>
                        <button type="button" class="ad-btn ad-btn--danger-outline" onclick="delete_car('${id}')" title="Удалить из лота">
                            <span class="icon-mbri-trash"></span>
                        </button>
                    </div>
                </div>
            </div>

            <!-- Hidden parameters for post and live math -->
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
        <div class="modal fade" id="cars_list_data_slug_${id}_modal" data-bs-backdrop="static" data-bs-keyboard="false" tabindex="-1" aria-labelledby="modal_title_${id}" aria-hidden="true">
            <div class="modal-dialog modal-xl modal-dialog-centered modal-dialog-scrollable">
                <div class="modal-content">
                    <div class="modal-header">
                        <div class="d-flex flex-column gap-1">
                            <div class="ad-modal-kicker">
                                <span class="icon-truck me-1"></span> КорсАвто • Студия подготовки автомобиля
                            </div>
                            <div class="d-flex flex-wrap align-items-center gap-2">
                                <h4 class="ad-modal-car-title" id="modal_title_${id}">
                                    ${mark} ${model}
                                </h4>
                                <span class="ad-car-chip"><span class="icon-mbri-calendar me-1"></span>${obj.year} г.в.</span>
                                <span class="ad-car-chip ad-car-chip--mono">
                                    VIN: ${obj.vin || '-'}
                                    ${obj.vin ? `
                                        <button type="button" class="ad-copy-btn ms-1" data-copy="${obj.vin}" title="Скопировать VIN">
                                            <span class="icon-mbri-file"></span>
                                        </button>
                                    ` : ''}
                                </span>
                            </div>
                        </div>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Закрыть"></button>
                    </div>
                    <div class="modal-body">
                        <!-- TABS NAVIGATION WITH HORIZONTAL SCROLL -->
                        <div class="ad-tabs-nav-wrap mb-4">
                            <div class="ad-tabs-nav">
                                <button type="button" class="ad-tab-btn active" data-target="tab_info_${id}">
                                    <span class="icon-mbri-info"></span> Сводка и комментарии
                                </button>
                                <button type="button" class="ad-tab-btn" data-target="tab_gallery_${id}">
                                    <span class="icon-mbri-preview"></span> Фотогалерея лота
                                </button>
                                <button type="button" class="ad-tab-btn" data-target="tab_diag_${id}">
                                    <span class="icon-mbri-setting2"></span> Диагностика и отчёты
                                </button>
                            </div>
                        </div>

                        <!-- TAB 1: INFO & COMMENTS -->
                        <div class="ad-tab-pane active" id="tab_info_${id}">
                            <div class="ad-modal-info-grid">
                                <div class="ad-modal-info-card">
                                    <div class="ad-modal-info-card__label"><span class="icon-mbri-speed me-1"></span> Пробег</div>
                                    <div class="ad-modal-info-card__value">${car_run} км</div>
                                </div>
                                <div class="ad-modal-info-card">
                                    <div class="ad-modal-info-card__label"><span class="icon-mbri-calendar me-1"></span> Дней на складе</div>
                                    <div class="ad-modal-info-card__value">${obj.days_in_stok || 0} д.</div>
                                </div>
                                <div class="ad-modal-info-card">
                                    <div class="ad-modal-info-card__label"><span class="icon-truck me-1"></span> Статус автомобиля</div>
                                    <div class="ad-modal-info-card__value">${obj.status_name || '-'}</div>
                                </div>
                                <div class="ad-modal-info-card">
                                    <div class="ad-modal-info-card__label"><span class="icon-mbri-cash me-1"></span> Себестоимость</div>
                                    <div class="ad-modal-info-card__value">${car_cost} ₽</div>
                                </div>
                                <div class="ad-modal-info-card">
                                    <div class="ad-modal-info-card__label"><span class="icon-mbri-delivery me-1"></span> Расходы</div>
                                    <div class="ad-modal-info-card__value">${car_outlay} ₽</div>
                                </div>
                                <div class="ad-modal-info-card ad-modal-info-card--sale">
                                    <div class="ad-modal-info-card__label"><span class="icon-mbri-cart-full me-1"></span> Базовая цена продажи</div>
                                    <div class="ad-modal-info-card__value">${car_price} ₽</div>
                                </div>
                            </div>

                            <div class="row g-3">
                                <div class="col-12 col-md-6">
                                    <label class="form-label mb-1">
                                        <span><span class="icon-mbri-setting2 text-warning me-1"></span> Комментарий для отдела подготовки</span>
                                    </label>
                                    <textarea class="form-control" name="cars_list_data_${id}_podgotovka" rows="5" placeholder="Укажите замечания по подготовке авто...">${obj.description_podgotovka || ''}</textarea>
                                </div>
                                <div class="col-12 col-md-6">
                                    <label class="form-label mb-1">
                                        <span><span class="icon-mbri-cart-full text-warning me-1"></span> Комментарий для отдела продаж</span>
                                    </label>
                                    <textarea class="form-control" name="cars_list_data_${id}_op" rows="5" placeholder="Укажите информацию для менеджеров ОП...">${obj.description_op || ''}</textarea>
                                </div>
                            </div>
                        </div>

                        <!-- TAB 2: GALLERY -->
                        <div class="ad-tab-pane" id="tab_gallery_${id}">
                            <div class="ad-modal-stub">
                                <div class="ad-modal-stub__icon">
                                    <span class="icon-mbri-preview"></span>
                                </div>
                                <div class="ad-modal-stub__title">Медиагалерея формируется</div>
                                <div class="ad-modal-stub__desc">
                                    Загрузка и распределение фотографий кузова, салона и повреждений станут доступны сразу после первого сохранения лота.
                                </div>
                            </div>
                        </div>

                        <!-- TAB 3: DIAGNOSTICS -->
                        <div class="ad-tab-pane" id="tab_diag_${id}">
                            <div class="ad-modal-stub">
                                <div class="ad-modal-stub__icon">
                                    <span class="icon-mbri-setting2"></span>
                                </div>
                                <div class="ad-modal-stub__title">Диагностические карты и акты осмотра</div>
                                <div class="ad-modal-stub__desc">
                                    Синхронизация сервисных карт, отчётов проверок и Autoteka будет выполнена автоматически после сохранения лота.
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="ad-btn ad-btn--outline" data-bs-dismiss="modal">
                            Закрыть
                        </button>
                        <button type="button" class="ad-btn ad-btn--primary ms-auto" data-bs-dismiss="modal">
                            <span class="icon-mbri-success me-1"></span> Применить
                        </button>
                    </div>
                </div>
            </div>
        </div>`;


        var sourceCard = document.getElementById('cars-list_data_' + id) || document.getElementById('cars-list_data_' + slug);
        var $newCard = $(html_card);

        $('#cars').append($newCard);
        $('body').append(modal_html);

        // Smoothly hide empty state
        if ($('#no_cars').length && !$('#no_cars').hasClass('d-none')) {
            $('#no_cars').addClass('d-none');
        }

        // Trigger smooth flight animation from drawer to deck
        if (sourceCard && $newCard.length) {
            animateCarTransfer(sourceCard, $newCard[0], function() {
                showAuctionToast(`Автомобиль ${mark} ${model} добавлен в лот!`, 'Успешно', 'success');
                sourceCard.style.opacity = '1';
            });
        } else {
            showAuctionToast(`Автомобиль ${mark} ${model} добавлен в лот!`, 'Успешно', 'success');
        }

        // Mark drawer source card as added
        if (sourceCard) {
            var $sc = $(sourceCard);
            $sc.addClass('is-in-lot');
            $sc.find('.ad-drawer-btn-add')
                .addClass('is-added')
                .html('<span class="icon-mbri-success me-1"></span><span>В лоте</span>')
                .attr('title', 'Автомобиль уже добавлен в лот');
            if (!$sc.find('.ad-drawer-card__badge-in-lot').length) {
                $sc.find('.ad-drawer-card__thumb').append(`
                    <span class="ad-drawer-card__badge-in-lot">
                        <span class="icon-mbri-success me-1"></span> В лоте
                    </span>
                `);
            }
        }

        refresh_board();
    }).fail(function() {
        showAuctionToast('Ошибка соединения при получении данных автомобиля', 'Ошибка', 'danger');
    });
}

/**
 * Smooth transfer animation from offcanvas drawer into main lot grid
 */
function animateCarTransfer(sourceEl, targetEl, callback) {
    if (!sourceEl || !targetEl) {
        if (callback) callback();
        return;
    }

    var startRect = sourceEl.getBoundingClientRect();

    // Create flying proxy clone
    var proxy = sourceEl.cloneNode(true);
    proxy.removeAttribute('id');
    proxy.classList.add('ad-flying-car-proxy');

    // Remove action buttons from flying clone
    var actions = proxy.querySelector('.ad-drawer-card__actions');
    if (actions) actions.remove();

    // Lock starting geometry with NO CSS transition yet (prevents browser starting glitch)
    proxy.style.position = 'fixed';
    proxy.style.top = startRect.top + 'px';
    proxy.style.left = startRect.left + 'px';
    proxy.style.width = startRect.width + 'px';
    proxy.style.height = startRect.height + 'px';
    proxy.style.margin = '0';
    proxy.style.transform = 'translate3d(0, 0, 0) scale(1)';
    proxy.style.opacity = '1';
    proxy.style.transition = 'none';

    document.body.appendChild(proxy);

    // Force reflow so the initial frame is guaranteed to be rendered
    void proxy.offsetHeight;

    // Dim source in drawer
    sourceEl.style.transition = 'opacity 0.3s ease';
    sourceEl.style.opacity = '0.35';

    // Target starts invisible while flight happens
    targetEl.classList.add('ad-car-card--incoming');

    // Check if target needs scrolling
    var endRect = targetEl.getBoundingClientRect();
    var isOffscreen = (endRect.top < 60 || endRect.bottom > window.innerHeight);

    if (isOffscreen) {
        targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    // Wait a brief tick for layout/scroll to stabilize before flight
    setTimeout(function() {
        endRect = targetEl.getBoundingClientRect();

        var deltaX = endRect.left - startRect.left;
        var deltaY = endRect.top - startRect.top;

        // Apply smooth GPU-accelerated transition
        proxy.style.transition = 'transform 0.85s cubic-bezier(0.16, 1, 0.3, 1), width 0.85s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.85s ease';
        proxy.style.transform = 'translate3d(' + deltaX + 'px, ' + deltaY + 'px, 0) scale(1)';
        proxy.style.width = Math.min(endRect.width, 500) + 'px';
        proxy.style.boxShadow = '0 20px 45px rgba(37, 99, 235, 0.25)';

        // Landing sequence
        setTimeout(function() {
            targetEl.classList.remove('ad-car-card--incoming');
            targetEl.classList.add('ad-car-card--landed');

            proxy.style.transition = 'opacity 0.25s ease, transform 0.25s ease';
            proxy.style.opacity = '0';
            proxy.style.transform = 'translate3d(' + deltaX + 'px, ' + deltaY + 'px, 0) scale(1.04)';

            setTimeout(function() {
                proxy.remove();
                setTimeout(function() {
                    targetEl.classList.remove('ad-car-card--landed');
                }, 1200);
                if (callback) callback();
            }, 250);
        }, 850);
    }, 90);
}

var carPendingDeletion = null;

function ensureDeleteModal() {
    var modalEl = document.getElementById('ad_delete_car_modal');
    if (!modalEl) {
        var modalHtml = `
        <div class="modal fade" id="ad_delete_car_modal" tabindex="-1" aria-labelledby="ad_delete_modal_label" aria-hidden="true" style="z-index: 1080;">
            <div class="modal-dialog modal-dialog-centered" style="max-width: 470px;">
                <div class="modal-content ad-delete-modal-content">
                    <div class="modal-header border-0 pb-0">
                        <div class="ad-modal-kicker text-danger" id="ad_delete_modal_label">
                            <span class="icon-mbri-alert me-1"></span> Подтверждение действия
                        </div>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Закрыть"></button>
                    </div>
                    <div class="modal-body text-center pt-2 pb-4">
                        <div class="ad-delete-icon-wrap mb-3">
                            <span class="icon-mbri-trash"></span>
                        </div>
                        <h4 class="ad-delete-modal-title mb-2">Удалить автомобиль?</h4>
                        <div class="ad-delete-car-preview mb-3" id="ad_delete_car_preview"></div>
                        <p class="ad-delete-modal-desc text-muted mb-0">
                            Автомобиль будет исключен из состава аукционного лота. Вы сможете добавить его снова при необходимости.
                        </p>
                    </div>
                    <div class="modal-footer border-0 pt-0 justify-content-center gap-2">
                        <button type="button" class="ad-btn ad-btn--outline px-4" data-bs-dismiss="modal">
                            Отмена
                        </button>
                        <button type="button" class="ad-btn ad-btn--danger px-4" id="ad_confirm_delete_btn">
                            <span class="icon-mbri-trash me-1"></span> Да, удалить
                        </button>
                    </div>
                </div>
            </div>
        </div>`;
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        modalEl = document.getElementById('ad_delete_car_modal');
    } else if (modalEl.parentElement !== document.body) {
        // Move directly to <body> to prevent stacking context traps
        document.body.appendChild(modalEl);
    }
    return modalEl;
}

// Ensure delete modal is placed at root of body on load
$(function() {
    ensureDeleteModal();
});

function delete_car(slug) {
    var $card = $('#cars_list_data_id_' + slug);
    if (!$card.length) return;

    var modalEl = ensureDeleteModal();

    var carTitle = $card.find('.ad-car-title').text().trim() || 'Автомобиль';
    var carMod = $card.find('.ad-car-modification').text().trim() || $card.find('.ad-car-mod').text().trim();
    var carVin = $card.find('[data-copy]').data('copy') || '';

    carPendingDeletion = slug;

    // Populate preview inside modal
    var previewHtml = `
        <div class="ad-delete-car-preview-card">
            <span class="ad-delete-car-preview-title">${carTitle}</span>
            ${carMod ? `<span class="ad-delete-car-preview-mod">${carMod}</span>` : ''}
            ${carVin ? `<span class="ad-car-chip ad-car-chip--mono py-0 px-2 small">VIN: ${carVin}</span>` : ''}
        </div>
    `;
    $('#ad_delete_car_preview').html(previewHtml);

    if (modalEl) {
        var modal = bootstrap.Modal.getOrCreateInstance(modalEl);
        modal.show();
    }
}

// Handle confirmed car removal
$(document).on('click', '#ad_confirm_delete_btn', function() {
    if (!carPendingDeletion) return;
    var slug = carPendingDeletion;
    carPendingDeletion = null;

    var modalEl = document.getElementById('ad_delete_car_modal');
    if (modalEl) {
        var modal = bootstrap.Modal.getInstance(modalEl);
        if (modal) modal.hide();
    }

    var $card = $('#cars_list_data_id_' + slug);
    var modalId = '#cars_list_data_slug_' + slug + '_modal';

    if (!$card.length) {
        $(modalId).remove();
        return;
    }

    // Trigger smooth departure animation
    $card.addClass('ad-car-card--deleting');

    setTimeout(function() {
        $card.slideUp(350, function() {
            $card.remove();
            $(modalId).remove();

            // If the deleted car is in the drawer, restore its active state
            var $sc = $('#cars-list_data_' + slug);
            if ($sc.length) {
                $sc.removeClass('is-in-lot');
                $sc.find('.ad-drawer-btn-add')
                    .removeClass('is-added')
                    .html('<span class="icon-mbri-plus me-1"></span><span>+ В лот</span>')
                    .attr('title', 'Добавить автомобиль в лот');
                $sc.find('.ad-drawer-card__badge-in-lot').remove();
            }

            // If no cars remaining in lot, smoothly restore the empty deck
            if ($('#cars .ad-car-card').length === 0) {
                $('#no_cars').removeClass('d-none').hide().fadeIn(300);
            }

            showAuctionToast('Автомобиль успешно удален из лота', 'Информация', 'info');
            refresh_board();
        });
    }, 450);
});

/* ==========================================================================
   OFFCANVAS DATA FETCHER & CAR PICKER
   ========================================================================== */
function visible_canvas() {
    var offcanvasElement = document.getElementById('offcanvasRight');
    if (offcanvasElement) {
        var storeName = $('#ad_store_label').text().trim() || $('select#store option:selected').text().trim();
        if (storeName && storeName !== '-- Выберите стоянку --') {
            $('#ad_drawer_store_name').text(storeName);
        } else {
            $('#ad_drawer_store_name').text('Стоянка размещения');
        }

        var offcanvas = bootstrap.Offcanvas.getOrCreateInstance(offcanvasElement);
        offcanvas.show();
        setTimeout(function() {
            $('#search').focus();
        }, 300);
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

function copyVinToClipboard(vin, event) {
    if (event) event.stopPropagation();
    if (!vin) return;
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(vin).then(function() {
            showAuctionToast('VIN скопирован: ' + vin, 'Буфер обмена', 'info');
        }).catch(function() {
            copyVinFallback(vin);
        });
    } else {
        copyVinFallback(vin);
    }
}

function copyVinFallback(vin) {
    var temp = $('<input>');
    $('body').append(temp);
    temp.val(vin).select();
    try {
        document.execCommand('copy');
        showAuctionToast('VIN скопирован: ' + vin, 'Буфер обмена', 'info');
    } catch(err) {
        showAuctionToast('VIN: ' + vin, 'VIN номер', 'info');
    }
    temp.remove();
}

function refresh_data_online() {
    var search = $('#search').val() || '';
    var url = '/auction/js/get_cars_lot_online/?store_id=' + store_id + '&search=' + encodeURIComponent(search) + '&page=' + page;

    var $refreshIcon = $('#refresh .icon-mbri-update');
    $refreshIcon.addClass('spin-icon');

    $.get(url, function(data) {
        $refreshIcon.removeClass('spin-icon');

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
            var vin = obj.vin || '';
            var photo = (obj.url && obj.url.length) ? (Array.isArray(obj.url) ? obj.url[0] : obj.url) : '';
            var isInLot = ($('#cars_list_data_id_' + id).length > 0);

            html += `
            <div id="cars-list_data_${id}" class="ad-drawer-card ${isInLot ? 'is-in-lot' : ''}" data-id="${id}" data-vin="${vin}">
                <div class="ad-drawer-card__thumb" onclick="info_car('${id}')" title="Нажмите для подробного просмотра">
                    ${photo && photo !== '/media/nophoto.png' ? `
                        <img src="${photo}" alt="${mark} ${model}" onerror="this.style.display='none'; if(this.nextElementSibling){this.nextElementSibling.style.display='flex';}">
                        <div class="ad-drawer-card__thumb-placeholder" style="display:none;">
                            <span class="icon-truck"></span>
                        </div>
                    ` : `
                        <div class="ad-drawer-card__thumb-placeholder">
                            <span class="icon-truck"></span>
                        </div>
                    `}
                    ${isInLot ? `
                        <span class="ad-drawer-card__badge-in-lot">
                            <span class="icon-mbri-success me-1"></span> В лоте
                        </span>
                    ` : ''}
                </div>

                <div class="ad-drawer-card__info">
                    <div class="d-flex align-items-start justify-content-between gap-1">
                        <div class="ad-drawer-card__title" onclick="info_car('${id}')" title="${mark} ${model}">
                            ${mark} ${model}
                        </div>
                    </div>

                    ${mod ? `<div class="ad-drawer-card__mod text-truncate" title="${mod}">${mod}</div>` : ''}

                    <div class="ad-drawer-card__chips">
                        <span class="ad-drawer-meta-chip"><span class="icon-mbri-calendar me-1"></span>${obj.year} г.</span>
                        <span class="ad-drawer-meta-chip font-monospace"><span class="icon-mbri-speed me-1"></span>${car_run} км</span>
                    </div>

                    ${vin ? `
                        <div class="ad-drawer-card__vin-wrap">
                            <span class="ad-drawer-vin font-monospace" title="Нажмите, чтобы скопировать VIN" onclick="copyVinToClipboard('${vin}', event)">
                                <span class="icon-mbri-code me-1"></span>${vin}
                            </span>
                        </div>
                    ` : ''}

                    <div class="d-flex align-items-center justify-content-between mt-auto pt-2">
                        <div class="ad-drawer-card__price">
                            ${car_price} ₽
                        </div>

                        <div class="ad-drawer-card__actions">
                            <button type="button" class="ad-drawer-btn-inspect" onclick="info_car('${id}')" title="Детальный осмотр и фото">
                                <span class="icon-mbri-preview"></span>
                            </button>
                            <button type="button" class="ad-drawer-btn-add ${isInLot ? 'is-added' : ''}" onclick="subbmit_car('${id}')" title="${isInLot ? 'Автомобиль уже добавлен в лот' : 'Добавить автомобиль в лот'}">
                                <span class="${isInLot ? 'icon-mbri-success' : 'icon-mbri-plus'} me-1"></span>
                                <span>${isInLot ? 'В лоте' : '+ В лот'}</span>
                            </button>
                        </div>
                    </div>
                </div>
            </div>`;
        }

        if (page === 0 && data.length === 0) {
            html = `
            <div class="ad-drawer-empty text-center py-5">
                <div class="ad-drawer-empty__icon mb-3">
                    <span class="icon-truck"></span>
                </div>
                <h6 class="fw-bold mb-1">Автомобили не найдены</h6>
                <p class="text-muted small mb-3">По вашему запросу на складе ничего не найдено</p>
                <button type="button" class="ad-btn ad-btn--sm ad-btn--outline" onclick="$('#search').val('').trigger('input');">
                    Сбросить поиск
                </button>
            </div>`;
            $('#ad_drawer_count_badge').text('0');
            $('#ad_drawer_status_text').text('Ничего не найдено');
        } else {
            var currentCount = (page === 0 ? data.length : ($('#cars-list .ad-drawer-card').length + data.length));
            $('#ad_drawer_count_badge').text(currentCount + (scroll_data ? '+' : ''));
            $('#ad_drawer_status_text').text('Показано: ' + currentCount + (scroll_data ? ' авто (есть еще)' : ' авто'));
        }

        var container = document.querySelector('#cars-list');
        if (container) {
            container.innerHTML = (page === 0 ? html : container.innerHTML + html);
        }

        // Reapply active filter if needed
        var activeFilter = $('.ad-drawer-chip-btn.active').data('filter');
        if (activeFilter === 'available') {
            $('#cars-list .ad-drawer-card.is-in-lot').hide();
        }

        visible_loader(false);
    }).fail(function() {
        $refreshIcon.removeClass('spin-icon');
        visible_loader(false);
        showAuctionToast('Ошибка при загрузке автомобилей со стоянки', 'Ошибка', 'danger');
    });
}

/* ==========================================================================
   CAR QUICK INSPECTION PREVIEW MODAL (OFFCANVAS ITEM PREVIEW)
   ========================================================================== */
function info_car(slug) {
    window.currentRlkCarSlug = slug;

    // Reset tabs to first tab (General info & prices)
    $('#rlk .ad-tab-btn, #rlk .ad-modal-tab-btn').removeClass('active');
    $('#rlk [data-target="tab_rlk_general"]').addClass('active');
    $('#rlk .ad-tab-pane').removeClass('active');
    $('#tab_rlk_general').addClass('active');

    // Show modal and preliminary loading state
    $('#rlk').modal('show');
    $('#info_car_name').html('<span class="spinner-border spinner-border-sm text-primary me-2"></span> Загрузка данных об автомобиле...');

    // Function to synchronize "Добавить в лот" button and in-lot status
    function updateRlkAddBtn(carSlug) {
        var isInLot = ($('#cars_list_data_id_' + carSlug).length > 0);
        var $btn = $('#rlk_btn_add_to_lot');
        if (isInLot) {
            $btn.removeClass('ad-btn--primary')
                .addClass('ad-btn--outline')
                .prop('disabled', false)
                .attr('title', 'Автомобиль уже добавлен в лот. Нажмите, чтобы закрыть окно')
                .html('<span class="icon-mbri-success text-success me-1"></span> Автомобиль в лоте');
            $('#info_car_in_lot_chip').show();
        } else {
            $btn.removeClass('ad-btn--outline')
                .addClass('ad-btn--primary')
                .prop('disabled', false)
                .attr('title', 'Добавить автомобиль в лот аукциона')
                .html('<span class="icon-mbri-plus me-1"></span> Добавить автомобиль в лот');
            $('#info_car_in_lot_chip').hide();
        }
    }

    updateRlkAddBtn(slug);

    // Bind click on "Автомобиль в лоте" or "Добавить автомобиль в лот": closes the modal window
    $('#rlk_btn_add_to_lot, #info_car_in_lot_chip').off('click').on('click', function() {
        var carSlug = window.currentRlkCarSlug;
        if (carSlug) {
            var isInLot = ($('#cars_list_data_id_' + carSlug).length > 0);
            if (!isInLot) {
                subbmit_car(carSlug);
            }
        }
        $('#rlk').modal('hide');
    });

    var url = '/auction/js/get_cars_lot_online/' + slug + '/';

    $.get(url, function(data) {
        if (!Array.isArray(data)) {
            data = data ? [data] : [];
        }
        if (!data.length) {
            $('#info_car_name').text('Автомобиль не найден');
            return;
        }

        var obj = data[0];
        var mark = obj.mark_name || '';
        var model = obj.model_name || '';
        var mod = obj.modification_name || '';
        var vin = obj.vin || '';
        var fmt = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 });

        var car_run = fmt.format(obj.run || 0);
        var car_price = fmt.format(obj.price || 0);
        var car_outlay = fmt.format(obj.outlay || 0);
        var car_bcp = fmt.format(obj.bcp || 0);
        var car_cost_price = fmt.format(obj.cost_price || 0);

        // Hero card
        $('#info_car_name').html(`${mark} ${model} ${mod} • ${obj.year} г.`);
        $('#info_car_hero_price').text(car_price + ' ₽');
        $('#info_car_type_sale').text('Продажа: ' + (obj.type_sale_name || '-'));
        $('#info_car_type_reception').text('Прием: ' + (obj.type_reception_name || '-'));
        $('#info_car_status_badge').text('Статус: ' + (obj.status_name || '-'));

        // Key parameters
        $('#info_car_run_value').text(car_run + ' км');
        $('#info_car_modification_value').text(mod || '-');
        $('#info_car_days_in_stok_value').text((obj.days_in_stok || 0) + ' д.');
        $('#info_car_status_name_value').text(obj.status_name || '-');
        $('#info_car_stage_price_value').text(obj.stage_price_name || '-');
        $('#info_car_vin_value').text(vin || '-');

        // Copy VIN handler
        $('#info_car_vin_copy_btn').off('click').on('click', function(e) {
            if (vin) {
                copyVinToClipboard(vin, e);
            }
        });

        // Financial indicators
        $('#info_car_price_value').text(car_price + ' ₽');
        $('#info_car_cost_price_value').text(car_cost_price + ' ₽');
        $('#info_car_bcp_value').text(car_bcp + ' ₽');
        $('#info_car_outlay_value').text(car_outlay + ' ₽');

        // Notes and textareas
        $('#info_car_description_podgotovka').val(obj.description_podgotovka || '');
        $('#info_car_description_op').val(obj.description_op || '');
        $('#info_car_comment_diagnostica').val(obj.int_ocenka_diagnostika || '');

        // Works list
        var worksText = '';
        if (obj.work_podgotovka && obj.work_podgotovka.length) {
            for (var w = 0; w < obj.work_podgotovka.length; w++) {
                worksText += (w + 1) + '. ' + obj.work_podgotovka[w].name + '\n';
            }
        }
        $('#work_car').val(worksText);

        // General Photos
        var photoHtml = '';
        var photoCount = 0;
        if (obj.url && obj.url.length) {
            var photosList = Array.isArray(obj.url) ? obj.url : [obj.url];
            for (var p = 0; p < photosList.length; p++) {
                var pUrl = photosList[p];
                if (pUrl && pUrl !== '/media/nophoto.png') {
                    photoCount++;
                    photoHtml += `
                    <div class="ad-photo-tile" title="Нажмите для увеличения">
                        <div class="ad-photo-tile__img-wrap">
                            <img src="${pUrl}" alt="Фото ${photoCount}" loading="lazy">
                        </div>
                    </div>`;
                }
            }
        }
        var photoContainer = document.querySelector('#info_car_photos');
        if (photoContainer) photoContainer.innerHTML = photoHtml;
        $('#badge_rlk_photos_count').text(photoCount);
        if (photoCount === 0) {
            $('#empty_car_photos').show();
        } else {
            $('#empty_car_photos').hide();
        }

        // Scheme Body Photos (6 projections)
        var schemeHtml = '';
        var schemeArr = [
            { url: obj.int_ocenka_url_pered, name: 'Спереди' },
            { url: obj.int_ocenka_url_right, name: 'Справа' },
            { url: obj.int_ocenka_url_zad, name: 'Сзади' },
            { url: obj.int_ocenka_url_left, name: 'Слева' },
            { url: obj.int_ocenka_url_up, name: 'Сверху' },
            { url: obj.int_ocenka_url_salon, name: 'Салон' }
        ];
        var schemeCount = 0;
        for (var sc = 0; sc < schemeArr.length; sc++) {
            if (schemeArr[sc].url) {
                schemeCount++;
                schemeHtml += `
                <div class="ad-photo-tile" title="${schemeArr[sc].name} - нажмите для увеличения">
                    <div class="ad-photo-tile__img-wrap">
                        <img src="${schemeArr[sc].url}" alt="${schemeArr[sc].name}" loading="lazy">
                    </div>
                </div>`;
            }
        }
        var schemeContainer = document.querySelector('#info_car_photos_int_body');
        if (schemeContainer) schemeContainer.innerHTML = schemeHtml;
        if (schemeCount === 0) {
            $('#empty_car_scheme').show();
        } else {
            $('#empty_car_scheme').hide();
        }

        // Damages Photos
        var damageHtml = '';
        var damageCount = 0;
        if (obj.int_ocenka_url_damage && obj.int_ocenka_url_damage.length) {
            var damageList = Array.isArray(obj.int_ocenka_url_damage) ? obj.int_ocenka_url_damage : [obj.int_ocenka_url_damage];
            for (var dm = 0; dm < damageList.length; dm++) {
                if (damageList[dm]) {
                    damageCount++;
                    damageHtml += `
                    <div class="ad-photo-tile" title="Дефект ${damageCount} - нажмите для увеличения">
                        <div class="ad-photo-tile__img-wrap">
                            <img src="${damageList[dm]}" alt="Повреждение ${damageCount}" loading="lazy">
                        </div>
                    </div>`;
                }
            }
        }
        var damageContainer = document.querySelector('#info_car_photos_damage');
        if (damageContainer) damageContainer.innerHTML = damageHtml;
        $('#badge_rlk_damage_count').text(damageCount);
        if (damageCount === 0) {
            $('#empty_car_damage').show();
        } else {
            $('#empty_car_damage').hide();
        }

        // Final sync of Add to Lot button state
        updateRlkAddBtn(slug);
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

    var $wrap = $('#wrap_store_combo');
    var $btn = $combo.find('.af-combo__btn');
    var $panel = $combo.find('.af-combo__panel');
    var $search = $combo.find('.af-combo__search');
    var $list = $combo.find('.af-combo__list');
    var $label = $('#ad_store_label');
    var $select = $('select#store');

    function openCombo() {
        // Close calendar if open
        if (typeof window.closeAuctionDateTimePicker === 'function') {
            window.closeAuctionDateTimePicker();
        } else {
            $('#ad_dt_picker').removeClass('is-open');
            $('#wrap_dt_picker').removeClass('is-open').css('z-index', '');
            $('#ad_cal_popup').attr('hidden', true).css('display', 'none');
            $('#ad_dt_trigger').attr('aria-expanded', 'false');
        }

        $combo.addClass('is-open');
        $wrap.addClass('is-open').css('z-index', '1050');
        $panel.removeAttr('hidden').css('display', 'flex');
        $btn.attr('aria-expanded', 'true');
        $search.val('').trigger('input');
        setTimeout(function() {
            $search.focus();
        }, 50);
    }

    function closeCombo() {
        $combo.removeClass('is-open');
        $wrap.removeClass('is-open').css('z-index', '');
        $panel.attr('hidden', true).css('display', 'none');
        $btn.attr('aria-expanded', 'false');
    }

    window.closeAuctionStoreCombo = closeCombo;

    // Toggle dropdown
    $btn.on('click', function(e) {
        e.stopPropagation();
        if ($combo.hasClass('is-open')) {
            closeCombo();
        } else {
            openCombo();
        }
    });

    // Search filter
    $search.on('input', function(e) {
        var query = ($(this).val() || '').toLowerCase().trim();
        var matchCount = 0;
        $list.find('.af-combo__option').each(function() {
            var text = ($(this).data('label') || $(this).text() || '').toLowerCase();
            if (!query || text.indexOf(query) !== -1) {
                $(this).removeClass('d-none');
                matchCount++;
            } else {
                $(this).addClass('d-none');
            }
        });
        var $empty = $panel.find('.af-combo__empty');
        if (matchCount === 0) {
            $empty.removeAttr('hidden').show();
        } else {
            $empty.attr('hidden', true).hide();
        }
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

        closeCombo();
    });

    // Prevent panel clicks from bubbling
    $panel.on('click', function(e) {
        e.stopPropagation();
    });

    // Close on outside click
    $(document).on('click', function(e) {
        if (!$(e.target).closest('#ad_store_combo, #wrap_store_combo').length) {
            closeCombo();
        }
    });

    // Close on Esc
    $(document).on('keydown', function(e) {
        if (e.key === 'Escape' && $combo.hasClass('is-open')) {
            closeCombo();
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

    var $wrapDt = $('#wrap_dt_picker');

    function openPicker() {
        if (typeof window.closeAuctionStoreCombo === 'function') {
            window.closeAuctionStoreCombo();
        } else {
            $('#ad_store_combo').removeClass('is-open');
            $('#wrap_store_combo').removeClass('is-open').css('z-index', '');
            $('#ad_store_combo .af-combo__panel').attr('hidden', true).css('display', 'none');
            $('#ad_store_combo .af-combo__btn').attr('aria-expanded', 'false');
        }

        $picker.addClass('is-open');
        $wrapDt.addClass('is-open').css('z-index', '1050');
        $popup.removeAttr('hidden').css('display', 'block');
        $trigger.attr('aria-expanded', 'true');
        viewYear = selectedYear;
        viewMonth = selectedMonth;
        renderGrid();
    }

    function closePicker() {
        $picker.removeClass('is-open');
        $wrapDt.removeClass('is-open').css('z-index', '');
        $popup.attr('hidden', true).css('display', 'none');
        $trigger.attr('aria-expanded', 'false');
    }

    window.closeAuctionDateTimePicker = closePicker;

    // Toggle Calendar Popup
    $trigger.on('click', function(e) {
        e.stopPropagation();
        if ($picker.hasClass('is-open')) {
            closePicker();
        } else {
            openPicker();
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

        closePicker();
    });

    // Prevent clicks inside popup from bubbling
    $popup.on('click', function(e) {
        e.stopPropagation();
    });

    // Close on outside click
    $(document).on('click', function(e) {
        if (!$(e.target).closest('#ad_dt_picker, #wrap_dt_picker').length) {
            closePicker();
        }
    });

    // Close on Esc
    $(document).on('keydown', function(e) {
        if (e.key === 'Escape' && $picker.hasClass('is-open')) {
            closePicker();
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

