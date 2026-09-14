(function () {
    const root = document.querySelector(".auction-floor");
    if (!root) return;

    const form = root.querySelector("#auctionFiltersForm");
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    function debounce(fn, wait) {
        let t;
        return function () {
            const ctx = this;
            const args = arguments;
            clearTimeout(t);
            t = setTimeout(function () {
                fn.apply(ctx, args);
            }, wait);
        };
    }

    function closeCombos(except) {
        root.querySelectorAll(".af-combo.is-open").forEach(function (combo) {
            if (combo !== except) setOpen(combo, false);
        });
    }

    function closeCal() {
        const wrap = root.querySelector("[data-af-cal]");
        if (!wrap) return;
        wrap.classList.remove("is-open");
        const cal = wrap.querySelector(".af-cal");
        if (cal) cal.hidden = true;
        wrap.querySelectorAll("[data-af-cal-open]").forEach(function (btn) {
            btn.classList.remove("is-active");
            btn.setAttribute("aria-expanded", "false");
        });
    }

    function closePopups(exceptCombo) {
        closeCombos(exceptCombo);
        if (!exceptCombo) closeCal();
    }

    function setOpen(combo, open) {
        combo.classList.toggle("is-open", open);
        const btn = combo.querySelector(".af-combo__btn");
        const panel = combo.querySelector(".af-combo__panel");
        if (btn) btn.setAttribute("aria-expanded", open ? "true" : "false");
        if (panel) panel.hidden = !open;
        if (open) {
            const search = combo.querySelector(".af-combo__search");
            if (search && !reduced) search.focus();
        }
    }

    function visibleOptions(combo) {
        return Array.prototype.filter.call(
            combo.querySelectorAll(".af-combo__option"),
            function (el) {
                return el.style.display !== "none";
            }
        );
    }

    function activate(combo, option) {
        visibleOptions(combo).forEach(function (el) {
            el.classList.toggle("is-active", el === option);
        });
        if (option) option.scrollIntoView({ block: "nearest" });
    }

    function filterOptions(combo, query) {
        const q = (query || "").trim().toLowerCase();
        let n = 0;
        combo.querySelectorAll(".af-combo__option").forEach(function (el) {
            const text = (el.textContent || "").toLowerCase();
            const show = !q || text.indexOf(q) !== -1;
            el.style.display = show ? "" : "none";
            if (show) n += 1;
        });
        const empty = combo.querySelector(".af-combo__empty");
        if (empty) empty.hidden = n > 0;
        const first = visibleOptions(combo)[0];
        if (first) activate(combo, first);
    }

    function selectOption(combo, option, submit) {
        if (!option) return;
        const hidden = combo.querySelector('input[type="hidden"]');
        const label = combo.querySelector(".af-combo__label");
        const lamp = combo.querySelector(".af-combo__value .af-lamp");
        if (hidden) hidden.value = option.getAttribute("data-value") || "";
        if (label) label.textContent = option.getAttribute("data-label") || option.textContent.trim();
        combo.querySelectorAll(".af-combo__option").forEach(function (el) {
            el.setAttribute("aria-selected", el === option ? "true" : "false");
        });
        if (lamp) {
            lamp.className = "af-lamp " + (option.getAttribute("data-lamp") || "");
        }
        setOpen(combo, false);
        if (submit && form) form.submit();
    }

    root.querySelectorAll("[data-af-combo]").forEach(function (combo) {
        const btn = combo.querySelector(".af-combo__btn");
        const search = combo.querySelector(".af-combo__search");
        const options = combo.querySelectorAll(".af-combo__option");

        btn.addEventListener("click", function (e) {
            e.preventDefault();
            const open = !combo.classList.contains("is-open");
            closeCombos(combo);
            closeCal();
            setOpen(combo, open);
        });

        btn.addEventListener("keydown", function (e) {
            if (e.key === "ArrowDown" || e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                closeCombos(combo);
                closeCal();
                setOpen(combo, true);
                activate(combo, visibleOptions(combo)[0]);
            }
        });

        if (search) {
            search.addEventListener("input", function () {
                filterOptions(combo, search.value);
            });
            search.addEventListener("keydown", function (e) {
                const vis = visibleOptions(combo);
                const current = combo.querySelector(".af-combo__option.is-active");
                const idx = vis.indexOf(current);
                if (e.key === "ArrowDown") {
                    e.preventDefault();
                    activate(combo, vis[Math.min(idx + 1, vis.length - 1)] || vis[0]);
                } else if (e.key === "ArrowUp") {
                    e.preventDefault();
                    activate(combo, vis[Math.max(idx - 1, 0)] || vis[0]);
                } else if (e.key === "Enter") {
                    e.preventDefault();
                    selectOption(combo, current || vis[0], true);
                } else if (e.key === "Escape") {
                    setOpen(combo, false);
                    btn.focus();
                }
            });
        }

        options.forEach(function (option) {
            option.addEventListener("click", function () {
                selectOption(combo, option, true);
            });
        });
    });

    document.addEventListener("click", function (e) {
        if (!e.target.closest(".af-combo") && !e.target.closest("[data-af-cal]")) {
            closeCombos();
            closeCal();
        }
    });

    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape") {
            closeCombos();
            closeCal();
            root.classList.remove("is-filters-open");
        }
    });

    const vin = root.querySelector("#vin");
    if (vin && form) {
        vin.addEventListener(
            "input",
            debounce(function () {
                if (vin.value.length === 0 || vin.value.length >= 6) form.submit();
            }, 500)
        );
        vin.addEventListener("keydown", function (e) {
            if (e.key === "Enter") {
                e.preventDefault();
                form.submit();
            }
        });
    }

    const MONTHS = ["январь","февраль","март","апрель","май","июнь","июль","август","сентябрь","октябрь","ноябрь","декабрь"];

    function pad2(n) {
        return n < 10 ? "0" + n : String(n);
    }

    function toISO(d) {
        return d.getFullYear() + "-" + pad2(d.getMonth() + 1) + "-" + pad2(d.getDate());
    }

    function fromISO(s) {
        if (!s) return null;
        const p = String(s).split("-");
        if (p.length !== 3) return null;
        const d = new Date(Number(p[0]), Number(p[1]) - 1, Number(p[2]));
        return isNaN(d.getTime()) ? null : d;
    }

    function fmtRu(s) {
        const d = fromISO(s);
        if (!d) return "";
        return pad2(d.getDate()) + "." + pad2(d.getMonth() + 1) + "." + d.getFullYear();
    }

    (function initCal() {
        const wrap = root.querySelector("[data-af-cal]");
        if (!wrap) return;
        const cal = wrap.querySelector(".af-cal");
        const grid = wrap.querySelector(".af-cal__grid");
        const title = wrap.querySelector(".af-cal__title");
        const fromInput = wrap.querySelector("#date_from");
        const toInput = wrap.querySelector("#date_to");
        const fromBtn = wrap.querySelector('[data-af-cal-open="from"]');
        const toBtn = wrap.querySelector('[data-af-cal-open="to"]');
        const clearBtn = wrap.querySelector("[data-af-clear-dates]");
        let view = fromISO(fromInput.value) || new Date();
        view = new Date(view.getFullYear(), view.getMonth(), 1);
        let active = "from";

        function syncLabels() {
            fromBtn.textContent = fmtRu(fromInput.value) || "от";
            toBtn.textContent = fmtRu(toInput.value) || "до";
            if (clearBtn) clearBtn.hidden = !(fromInput.value || toInput.value);
        }

        function paint() {
            const y = view.getFullYear();
            const m = view.getMonth();
            title.textContent = MONTHS[m] + " " + y;
            const first = new Date(y, m, 1);
            const offset = (first.getDay() + 6) % 7;
            const days = new Date(y, m + 1, 0).getDate();
            const prevDays = new Date(y, m, 0).getDate();
            const fromV = fromInput.value;
            const toV = toInput.value;
            const today = toISO(new Date());
            grid.innerHTML = "";
            for (let i = 0; i < 42; i++) {
                const cell = document.createElement("button");
                cell.type = "button";
                cell.className = "af-cal__day";
                let day;
                let month = m;
                let year = y;
                if (i < offset) {
                    day = prevDays - offset + i + 1;
                    month = m - 1;
                    if (month < 0) { month = 11; year -= 1; }
                    cell.classList.add("is-mute");
                } else if (i >= offset + days) {
                    day = i - offset - days + 1;
                    month = m + 1;
                    if (month > 11) { month = 0; year += 1; }
                    cell.classList.add("is-mute");
                } else {
                    day = i - offset + 1;
                }
                const iso = year + "-" + pad2(month + 1) + "-" + pad2(day);
                cell.textContent = String(day);
                cell.setAttribute("data-iso", iso);
                if (iso === today) cell.classList.add("is-today");
                if (iso === fromV) cell.classList.add("is-from", "is-pick");
                if (iso === toV) cell.classList.add("is-to", "is-pick");
                if (fromV && toV && iso > fromV && iso < toV) cell.classList.add("is-range");
                cell.addEventListener("click", function () {
                    if (active === "from") {
                        fromInput.value = iso;
                        if (toInput.value && toInput.value < iso) toInput.value = "";
                    } else {
                        toInput.value = iso;
                        if (fromInput.value && fromInput.value > iso) fromInput.value = iso;
                    }
                    syncLabels();
                    paint();
                    if (form) form.submit();
                });
                grid.appendChild(cell);
            }
        }

        function openCal(which) {
            closeCombos();
            active = which;
            wrap.classList.add("is-open");
            cal.hidden = false;
            fromBtn.classList.toggle("is-active", which === "from");
            toBtn.classList.toggle("is-active", which === "to");
            fromBtn.setAttribute("aria-expanded", which === "from" ? "true" : "false");
            toBtn.setAttribute("aria-expanded", which === "to" ? "true" : "false");
            const seed = fromISO(which === "to" ? toInput.value || fromInput.value : fromInput.value);
            if (seed) view = new Date(seed.getFullYear(), seed.getMonth(), 1);
            paint();
        }

        fromBtn.addEventListener("click", function (e) {
            e.preventDefault();
            openCal("from");
        });
        toBtn.addEventListener("click", function (e) {
            e.preventDefault();
            openCal("to");
        });
        wrap.querySelector("[data-af-cal-prev]").addEventListener("click", function () {
            view = new Date(view.getFullYear(), view.getMonth() - 1, 1);
            paint();
        });
        wrap.querySelector("[data-af-cal-next]").addEventListener("click", function () {
            view = new Date(view.getFullYear(), view.getMonth() + 1, 1);
            paint();
        });
        if (clearBtn) {
            clearBtn.addEventListener("click", function () {
                fromInput.value = "";
                toInput.value = "";
                if (form) form.submit();
            });
        }
        syncLabels();
    })();

    const openFilters = root.querySelector("[data-af-open-filters]");
    const closeFilters = root.querySelector("[data-af-close-filters]");
    const backdrop = root.querySelector(".af-sheet-backdrop");
    function setFiltersOpen(open) {
        root.classList.toggle("is-filters-open", open);
        if (openFilters) openFilters.setAttribute("aria-expanded", open ? "true" : "false");
    }
    if (openFilters) {
        openFilters.addEventListener("click", function () {
            setFiltersOpen(true);
        });
    }
    if (closeFilters) {
        closeFilters.addEventListener("click", function () {
            setFiltersOpen(false);
        });
    }
    if (backdrop) {
        backdrop.addEventListener("click", function () {
            setFiltersOpen(false);
        });
    }

    root.querySelectorAll(".af-row[data-href]").forEach(function (row) {
        row.addEventListener("click", function (e) {
            if (e.target.closest("a, button")) return;
            window.location.href = row.getAttribute("data-href");
        });
        row.addEventListener("keydown", function (e) {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                window.location.href = row.getAttribute("data-href");
            }
        });
    });

    // ==== Сортировка колонок ====
    root.querySelectorAll("[data-af-sort]").forEach(function (btn) {
        btn.addEventListener("click", function () {
            const field = btn.getAttribute("data-af-sort");
            const sortInput = form && form.querySelector('input[name="sort"]');
            if (!sortInput) return;
            const current = sortInput.value || "";
            if (current === field) {
                sortInput.value = "-" + field;
            } else if (current === "-" + field) {
                sortInput.value = "";
            } else {
                sortInput.value = field;
            }
            if (form) form.submit();
        });
    });

    function countFilters() {
        if (!form) return 0;
        let n = 0;
        ["status", "store_id", "vin", "date_from", "date_to", "express"].forEach(function (name) {
            const el = form.querySelector('[name="' + name + '"]');
            if (el && String(el.value || "").trim()) n += 1;
        });
        return n;
    }
    const badge = root.querySelector("[data-af-filter-count]");
    if (badge) {
        const n = countFilters();
        badge.textContent = String(n);
        badge.hidden = n === 0;
    }

    // ==== Копирование номера лота / VIN ====
    const toastEl = document.getElementById("afToast");
    const toastText = document.getElementById("afToastText");
    let toastTimer;

    function showToast(message) {
        if (!toastEl || !toastText) return;
        toastText.textContent = message;
        toastEl.hidden = false;
        void toastEl.offsetWidth;
        toastEl.classList.add("is-show");
        clearTimeout(toastTimer);
        toastTimer = setTimeout(function () {
            toastEl.classList.remove("is-show");
            setTimeout(function () {
                if (!toastEl.classList.contains("is-show")) {
                    toastEl.hidden = true;
                }
            }, 300);
        }, 2200);
    }

    function copyToClipboard(text, onSuccess, onError) {
        if (!text) return;
        if (navigator.clipboard && window.isSecureContext) {
            navigator.clipboard.writeText(text).then(onSuccess).catch(function () {
                fallbackCopy(text, onSuccess, onError);
            });
        } else {
            fallbackCopy(text, onSuccess, onError);
        }
    }

    function fallbackCopy(text, onSuccess, onError) {
        try {
            const ta = document.createElement("textarea");
            ta.value = text;
            ta.style.position = "fixed";
            ta.style.top = "-9999px";
            ta.style.left = "-9999px";
            ta.setAttribute("readonly", "");
            document.body.appendChild(ta);
            ta.focus();
            ta.select();
            const ok = document.execCommand("copy");
            document.body.removeChild(ta);
            if (ok) {
                if (onSuccess) onSuccess();
            } else {
                if (onError) onError();
            }
        } catch (err) {
            if (onError) onError(err);
        }
    }

    root.querySelectorAll("[data-af-copy]").forEach(function (btn) {
        btn.addEventListener("click", function (e) {
            e.preventDefault();
            e.stopPropagation();
            const val = (btn.getAttribute("data-af-copy") || "").trim();
            const label = btn.getAttribute("data-af-copy-label") || val;
            if (!val) return;

            copyToClipboard(val, function () {
                btn.classList.add("is-copied");
                showToast("Скопировано: " + label);
                setTimeout(function () {
                    btn.classList.remove("is-copied");
                }, 1500);
            }, function () {
                showToast("Не удалось скопировать");
            });
        });
    });

    const helpData = {
        createLot: {
            title: "Создание нового лота",
            paragraphs: [
                "При переходе на форму создания нового лота создаётся черновик аукциона: выберите дилерский центр, задайте стартовую цену и дату старта торгов, заполните текстовое описание лота.",
                "Добавьте автомобили из каталога организации: для каждого заполняйте результаты диагностики, план работ, комментарии по подготовке, прикрепляйте фотографии по категориям (диагностика, колёса, повреждения, схема, салон и внешний вид).",
                "Каждая загрузка сохраняется в карточке: можно отметить наличие отчёта «Автотека», статус «Проверено», добавить ссылки на мультимедиа и пересчитать стоимость при изменении данных.",
                "Используйте черновое сохранение, обновление (кнопка «Обновить») и окончательную отправку: после проверки всех автомобилей отправьте лот на торги, чтобы его увидели дилеры и партнёры."
            ]
        },
        monitorStats: {
            title: "Мониторинг ключевых показателей",
            paragraphs: [
                "Верхние карточки отображают текущее количество активных аукционов, суммарную стартовую стоимость и число автомобилей — данные подтягиваются из базы и обновляются после каждого сохранения лота.",
                "При редактировании лота выполняется пересчёт (функция обновления), который учитывает изменения стоимости, статуса автомобильных карточек и наличие фото/отчётов, поэтому статистика на главной странице всегда актуальна.",
                "Используйте показатели, чтобы отслеживать динамику: фильтруйте аукционы, сравнивайте суммы и оперативно реагируйте на отклонения."
            ]
        },
        filterManagement: {
            title: "Управление фильтрами",
            paragraphs: [
                "Лента фильтров задаёт статус, стоянку, период и VIN. Списки — кастомные: поиск по названию, выбор с клавиатуры.",
                "Активные условия остаются в адресе страницы (GET), поэтому набор можно сохранить в закладках.",
                "На телефоне фильтры открываются нижней панелью, это та же форма, что и на десктопе."
            ]
        },
        lotCard: {
            title: "Работа со строкой лота",
            paragraphs: [
                "Строка показывает номер лота, статус, автомобили, старт, стоянку, цену и победителя, если он уже есть.",
                "Клик по строке или кнопка «Открыть» ведёт в карточку аукциона для правки и отправки."
            ]
        }
    };

    function initHelp() {
        const helpModal = document.getElementById("auctionHelpModal");
        const detailModal = document.getElementById("auctionHelpDetailModal");
        if (!helpModal || !detailModal || typeof bootstrap === "undefined") return;
        const detailTitle = detailModal.querySelector(".modal-title");
        const detailBody = detailModal.querySelector(".auction-help-detail-body");
        const detailVideoWrapper = detailModal.querySelector(".auction-help-detail-video-wrapper");
        const detailVideoFrame = detailModal.querySelector(".auction-help-detail-video");
        helpModal.querySelectorAll(".help-detail-trigger").forEach(function (trigger) {
            trigger.addEventListener("click", function () {
                const sectionId = this.getAttribute("data-section-id");
                const section = helpData[sectionId];
                if (!section) return;
                if (detailTitle) detailTitle.textContent = section.title;
                if (detailBody) {
                    detailBody.innerHTML = section.paragraphs.map(function (p) {
                        return "<p>" + p + "</p>";
                    }).join("");
                }
                if (detailVideoWrapper && detailVideoFrame) {
                    const video = this.getAttribute("data-video");
                    if (video) {
                        detailVideoFrame.src = video;
                        detailVideoFrame.muted = true;
                        detailVideoWrapper.classList.remove("d-none");
                    } else {
                        detailVideoFrame.pause();
                        detailVideoFrame.removeAttribute("src");
                        detailVideoWrapper.classList.add("d-none");
                    }
                }
                const helpInstance = bootstrap.Modal.getInstance(helpModal);
                if (helpInstance) helpInstance.hide();
                bootstrap.Modal.getOrCreateInstance(detailModal).show();
            });
        });
        detailModal.addEventListener("hidden.bs.modal", function () {
            if (detailVideoFrame) {
                detailVideoFrame.pause();
                detailVideoFrame.removeAttribute("src");
            }
            if (detailVideoWrapper) detailVideoWrapper.classList.add("d-none");
            bootstrap.Modal.getOrCreateInstance(helpModal).show();
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initHelp);
    } else {
        initHelp();
    }
})();
