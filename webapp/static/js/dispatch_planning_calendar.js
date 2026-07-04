document.addEventListener('DOMContentLoaded', function () {
    const page = document.querySelector('.dispatch-calendar-page');
    const calendarEl = document.getElementById('dispatch-calendar');
    const messageEl = document.getElementById('dispatch-calendar-message');
    const capacityEl = document.getElementById('dispatch-capacity-strip');
    const noteListEl = document.getElementById('dispatch-note-list');
    const modalEl = $('#dispatch-event-modal');

    if (!page || !calendarEl || typeof FullCalendar === 'undefined') {
        return;
    }

    function showMessage(text, kind) {
        messageEl.className = 'alert alert-' + kind + ' mb-0 py-2';
        messageEl.textContent = text;
        messageEl.classList.remove('d-none');
        window.setTimeout(function () {
            messageEl.classList.add('d-none');
        }, 5000);
    }


    function endpoint(template, id) {
        return template.replace('/0/', '/' + id + '/');
    }

    function todayIso() {
        return new Date().toISOString().substring(0, 10);
    }

    function filterParams(rangeInfo) {
        const params = new URLSearchParams();
        const driver = document.getElementById('dispatch-filter-driver').value;
        const customer = document.getElementById('dispatch-filter-customer').value;
        const status = document.getElementById('dispatch-filter-status').value;
        const terminal = document.getElementById('dispatch-filter-terminal').value;
        const range = document.getElementById('dispatch-filter-range').value;
        const search = document.getElementById('dispatch-filter-search').value.trim();
        const today = new Date();
        let start = rangeInfo ? rangeInfo.startStr.substring(0, 10) : '';
        let end = rangeInfo ? rangeInfo.endStr.substring(0, 10) : '';

        if (range === 'today') {
            start = today.toISOString().substring(0, 10);
            end = start;
        } else if (range === '7' || range === '30') {
            const finish = new Date(today);
            finish.setDate(finish.getDate() + parseInt(range, 10));
            start = today.toISOString().substring(0, 10);
            end = finish.toISOString().substring(0, 10);
        } else if (range === 'all') {
            start = '';
            end = '';
        }

        if (start) params.set('start', start);
        if (end) params.set('end', end);
        if (driver) params.set('driver', driver);
        if (customer) params.set('customer', customer);
        if (status) params.set('status', status);
        if (terminal) params.set('terminal', terminal);
        if (search) params.set('search', search);
        if (range) params.set('range', range);
        return params;
    }

    function applyInvoiceColorMode() {
        const enabled = document.getElementById('dispatch-filter-show-invoiced').checked;
        page.classList.toggle('dispatch-show-invoiced', enabled);
    }

    function currentRangeInfo() {
        return {
            startStr: calendar.view.activeStart.toISOString(),
            endStr: calendar.view.activeEnd.toISOString()
        };
    }

    function renderCapacity(items) {
        capacityEl.innerHTML = '';
        if (!items.length) {
            capacityEl.innerHTML = '<div class="text-muted">No scheduled jobs in this range.</div>';
            return;
        }
        items.slice(0, 21).forEach(function (item) {
            const div = document.createElement('div');
            div.className = 'dispatch-capacity-day';
            if (item.over_capacity) div.classList.add('dispatch-capacity-over');
            if (item.lfd_near || item.lfd_past || item.due_back_near || item.due_back_past) div.classList.add('dispatch-capacity-lfd');
            div.innerHTML = [
                '<strong>' + item.date + '</strong>',
                '<span>' + item.scheduled + ' scheduled / ' + (item.capacity || 0) + ' capacity</span>',
                item.driver_off ? '<div>' + item.driver_off + ' driver off</div>' : '',
                item.port_closed ? '<div>Port closed</div>' : '',
                item.port_early_close ? '<div>Port early close</div>' : '',
                item.lfd_past ? '<div>' + item.lfd_past + ' past LFD</div>' : '',
                item.lfd_near ? '<div>' + item.lfd_near + ' near LFD</div>' : '',
                item.due_back_past ? '<div>' + item.due_back_past + ' past due back</div>' : '',
                item.due_back_near ? '<div>' + item.due_back_near + ' near due back</div>' : ''
            ].join('');
            capacityEl.appendChild(div);
        });
    }

    function refreshCapacity(rangeInfo) {
        const params = filterParams(rangeInfo || calendar.view);
        fetch(page.dataset.capacityUrl + '?' + params.toString())
            .then(response => response.json())
            .then(renderCapacity)
            .catch(() => showMessage('Could not load capacity summary.', 'danger'));
    }

    function refreshNotes(rangeInfo) {
        const params = filterParams(rangeInfo || calendar.view);
        fetch(page.dataset.notesUrl + '?' + params.toString())
            .then(response => response.json())
            .then(renderNotes)
            .catch(() => showMessage('Could not load dispatch notes.', 'danger'));
    }

    function renderNotes(notes) {
        noteListEl.innerHTML = '';
        if (!notes.length) {
            noteListEl.innerHTML = '<div class="text-muted small">No special notes in this range.</div>';
            return;
        }
        notes.slice(0, 30).forEach(function (note) {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'dispatch-note-chip dispatch-note-chip-' + note.type;
            button.dataset.note = JSON.stringify(note);
            button.innerHTML = [
                '<strong>' + note.date + '</strong>',
                '<span>' + note.label + '</span>',
                note.notes ? '<small>' + note.notes + '</small>' : ''
            ].join('');
            button.addEventListener('click', function () {
                fillNoteForm(JSON.parse(this.dataset.note));
            });
            noteListEl.appendChild(button);
        });
    }

    function eventDetailsHtml(event) {
        const p = event.extendedProps;
        const rows = [
            ['JO', p.jo],
            ['Container', p.container]
        ];
        if (p.booking_display_mode === 'split') {
            rows.push(['Out-Booking', p.booking]);
            rows.push(['In-Booking', p.in_booking]);
        } else {
            rows.push(['Booking', p.booking || p.in_booking]);
        }
        rows.push(
            ['Customer', p.customer],
            ['Delivery', p.delivery_location || p.delivery_city_state || p.delivery],
            ['Driver', p.driver],
            ['Truck', p.truck],
            ['Appointment', p.appointment_time],
            ['Status', p.status],
            ['PIN', p.pin_status]
        );
        return '<dl>' + rows.map(function (row) {
            return '<dt>' + row[0] + '</dt><dd>' + (row[1] || '-') + '</dd>';
        }).join('') + '</dl>';
    }

    function addBusinessDays(dateValue, days) {
        if (!dateValue) return '';
        const date = new Date(dateValue + 'T00:00:00');
        let added = 0;
        while (added < days) {
            date.setDate(date.getDate() + 1);
            const day = date.getDay();
            if (day === 0 || day === 6) continue;
            added += 1;
        }
        return date.toISOString().substring(0, 10);
    }

    function setFieldVisibility(selector, visible) {
        document.querySelectorAll(selector).forEach(function (el) {
            el.classList.toggle('d-none', !visible);
        });
    }

    function configureDateFields(p) {
        setFieldVisibility('.dispatch-date-ship-arrive-field', !!p.is_import);
        setFieldVisibility('.dispatch-date-dp-field', !!p.is_drop_pick);
        document.getElementById('dispatch-modal-ship-arrive-date').dataset.autoAdjust = (p.is_import && p.pull_status === 'unpulled') ? '1' : '';
    }

    function openEventModal(event) {
        const p = event.extendedProps;
        if (p.is_port_closure) {
            const year = (p.note_date || event.startStr || '').substring(0, 4);
            const target = page.dataset.portClosuresUrl + (year ? '?year=' + encodeURIComponent(year) : '');
            window.location.href = target;
            return;
        }
        if (p.is_note) {
            fillNoteForm({
                id: p.note_id,
                date: p.note_date,
                type: p.note_type,
                driver: p.driver,
                port: p.port,
                close_time: p.close_time,
                notes: p.notes,
                label: event.title
            });
            return;
        }
        document.getElementById('dispatch-modal-order-id').value = event.id;
        document.getElementById('dispatch-event-modal-title').textContent = p.container || p.jo || 'Dispatch Job';
        document.getElementById('dispatch-modal-summary').innerHTML = eventDetailsHtml(event);
        document.getElementById('dispatch-modal-date').value = p.scheduled_date || event.startStr.substring(0, 10);
        document.getElementById('dispatch-modal-time').value = p.scheduled_time || '';
        document.getElementById('dispatch-modal-driver').value = p.driver || '';
        document.getElementById('dispatch-modal-truck').value = p.truck || '';
        document.getElementById('dispatch-modal-status').value = p.status || '';
        document.getElementById('dispatch-modal-notes').value = p.notes || '';
        document.getElementById('dispatch-modal-pull-date').value = p.pull_date || '';
        document.getElementById('dispatch-modal-return-date').value = p.return_date || '';
        document.getElementById('dispatch-modal-delivery-date').value = p.delivery_date || '';
        document.getElementById('dispatch-modal-delivery-time').value = p.appointment_time || '';
        document.getElementById('dispatch-modal-first-available-date').value = p.first_available_date || '';
        document.getElementById('dispatch-modal-port-deadline-date').value = p.port_deadline_date || '';
        document.getElementById('dispatch-modal-ship-arrive-date').value = p.ship_arrive_date || '';
        document.getElementById('dispatch-modal-due-back-date').value = p.due_back_date || '';
        document.getElementById('dispatch-modal-secondary-action-date').value = p.secondary_action_date || '';
        configureDateFields(p);
        modalEl.modal('show');
    }

    function noteTypeChanged() {
        const type = document.getElementById('dispatch-note-type').value;
        document.querySelector('.dispatch-note-driver-field').classList.toggle('d-none', type !== 'driver_off');
        document.querySelector('.dispatch-note-port-field').classList.toggle('d-none', type === 'driver_off');
        document.querySelector('.dispatch-note-time-field').classList.toggle('d-none', type !== 'port_early_close');
    }

    function clearNoteForm(dateValue) {
        document.getElementById('dispatch-note-id').value = '';
        document.getElementById('dispatch-note-date').value = dateValue || todayIso();
        document.getElementById('dispatch-note-end-date').value = '';
        document.getElementById('dispatch-note-type').value = 'driver_off';
        document.getElementById('dispatch-note-driver').value = '';
        document.getElementById('dispatch-note-port').value = 'Baltimore Seagirt';
        document.getElementById('dispatch-note-close-time').value = '';
        document.getElementById('dispatch-note-text').value = '';
        document.getElementById('dispatch-note-delete').classList.add('d-none');
        noteTypeChanged();
    }

    function fillNoteForm(note) {
        document.getElementById('dispatch-note-id').value = note.id || '';
        document.getElementById('dispatch-note-date').value = note.date || todayIso();
        document.getElementById('dispatch-note-end-date').value = '';
        document.getElementById('dispatch-note-type').value = note.type || 'driver_off';
        document.getElementById('dispatch-note-driver').value = note.driver || '';
        document.getElementById('dispatch-note-port').value = note.port || 'Baltimore Seagirt';
        document.getElementById('dispatch-note-close-time').value = note.close_time || '';
        document.getElementById('dispatch-note-text').value = note.notes || '';
        document.getElementById('dispatch-note-delete').classList.toggle('d-none', !note.id);
        noteTypeChanged();
        showMessage('Loaded note for editing.', 'info');
    }

    const calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        height: 'auto',
        editable: true,
        eventResizableFromStart: true,
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,timeGridDay,listWeek'
        },
        events: function (fetchInfo, successCallback, failureCallback) {
            const params = filterParams(fetchInfo);
            fetch(page.dataset.eventsUrl + '?' + params.toString())
                .then(response => response.json())
                .then(successCallback)
                .catch(failureCallback);
        },
        datesSet: function (info) {
            refreshCapacity(info);
            refreshNotes(info);
        },
        dateClick: function (info) {
            clearNoteForm(info.dateStr);
        },
        eventClick: function (info) {
            openEventModal(info.event);
        },
        eventDrop: function (info) {
            const url = endpoint(page.dataset.moveUrlTemplate, info.event.id);
            fetch(url, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({start: info.event.startStr})
            })
                .then(response => response.json().then(data => ({ok: response.ok, data: data})))
                .then(result => {
                    if (!result.ok || !result.data.ok) {
                        throw new Error(result.data.error || 'Move was rejected.');
                    }
                    showMessage('Dispatch date updated.', 'success');
                    calendar.refetchEvents();
                    refreshCapacity(currentRangeInfo());
                })
                .catch(error => {
                    info.revert();
                    showMessage(error.message, 'danger');
                });
        },
        eventResize: function (info) {
            info.revert();
            showMessage('Use the job modal to set appointment time.', 'warning');
        },
        eventContent: function (arg) {
            const p = arg.event.extendedProps;
            if (p.is_port_closure) {
                return {html: '<div><strong>' + arg.event.title + '</strong></div>'};
            }
            if (p.is_note) {
                return {html: '<div><strong>' + arg.event.title + '</strong>' + (p.notes ? '<div>' + p.notes + '</div>' : '') + '</div>'};
            }
            const dateLine = p.calendar_date_line || (p.deadline_date ? (p.deadline_label + ' ' + p.deadline_date) : '');
            let lines;
            if (p.appointment_time && !p.calendar_compact) {
                lines = [
                    p.calendar_appointment_line || arg.event.title,
                    p.shipper || p.customer,
                    dateLine
                ].filter(Boolean);
            } else {
                lines = [
                    p.calendar_title_line || arg.event.title,
                    dateLine
                ].filter(Boolean);
            }
            return {html: '<div>' + lines.map(line => '<div>' + line + '</div>').join('') + '</div>'};
        }
    });

    calendar.render();
    applyInvoiceColorMode();

    let filterTimer = null;
    document.querySelectorAll('.dispatch-filter').forEach(function (el) {
        el.addEventListener('change', function () {
            applyInvoiceColorMode();
            calendar.refetchEvents();
            refreshCapacity(currentRangeInfo());
            refreshNotes(currentRangeInfo());
        });
    });
    document.getElementById('dispatch-filter-search').addEventListener('input', function () {
        window.clearTimeout(filterTimer);
        filterTimer = window.setTimeout(function () {
            calendar.refetchEvents();
            refreshCapacity(currentRangeInfo());
            refreshNotes(currentRangeInfo());
        }, 250);
    });

    document.getElementById('dispatch-modal-ship-arrive-date').addEventListener('change', function () {
        if (this.dataset.autoAdjust !== '1' || !this.value) {
            return;
        }
        document.getElementById('dispatch-modal-first-available-date').value = this.value;
        document.getElementById('dispatch-modal-port-deadline-date').value = addBusinessDays(this.value, 3);
    });

    document.getElementById('dispatch-modal-pull-date').addEventListener('change', function () {
        document.getElementById('dispatch-modal-due-back-date').value = addBusinessDays(this.value, 4);
    });

    document.getElementById('dispatch-event-form').addEventListener('submit', function (event) {
        event.preventDefault();
        const orderId = document.getElementById('dispatch-modal-order-id').value;
        const payload = {
            scheduled_date: document.getElementById('dispatch-modal-date').value,
            scheduled_time: document.getElementById('dispatch-modal-time').value,
            driver: document.getElementById('dispatch-modal-driver').value,
            truck: document.getElementById('dispatch-modal-truck').value,
            status: document.getElementById('dispatch-modal-status').value,
            notes: document.getElementById('dispatch-modal-notes').value,
            pull_date: document.getElementById('dispatch-modal-pull-date').value,
            return_date: document.getElementById('dispatch-modal-return-date').value,
            delivery_date: document.getElementById('dispatch-modal-delivery-date').value,
            delivery_time: document.getElementById('dispatch-modal-delivery-time').value,
            first_available_date: document.getElementById('dispatch-modal-first-available-date').value,
            port_deadline_date: document.getElementById('dispatch-modal-port-deadline-date').value,
            ship_arrive_date: document.getElementById('dispatch-modal-ship-arrive-date').value,
            due_back_date: document.getElementById('dispatch-modal-due-back-date').value,
            secondary_action_date: document.getElementById('dispatch-modal-secondary-action-date').value
        };
        fetch(endpoint(page.dataset.updateUrlTemplate, orderId), {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        })
            .then(response => response.json().then(data => ({ok: response.ok, data: data})))
            .then(result => {
                if (!result.ok || !result.data.ok) {
                    throw new Error(result.data.error || 'Update was rejected.');
                }
                modalEl.modal('hide');
                showMessage('Dispatch plan updated.', 'success');
                calendar.refetchEvents();
                refreshCapacity(currentRangeInfo());
            })
            .catch(error => showMessage(error.message, 'danger'));
    });

    document.getElementById('dispatch-note-type').addEventListener('change', noteTypeChanged);
    document.getElementById('dispatch-note-clear').addEventListener('click', function () {
        clearNoteForm();
    });
    document.getElementById('dispatch-note-form').addEventListener('submit', function (event) {
        event.preventDefault();
        const payload = {
            id: document.getElementById('dispatch-note-id').value,
            date: document.getElementById('dispatch-note-date').value,
            end_date: document.getElementById('dispatch-note-end-date').value,
            type: document.getElementById('dispatch-note-type').value,
            driver: document.getElementById('dispatch-note-driver').value,
            port: document.getElementById('dispatch-note-port').value,
            close_time: document.getElementById('dispatch-note-close-time').value,
            notes: document.getElementById('dispatch-note-text').value
        };
        fetch(page.dataset.noteSaveUrl, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        })
            .then(response => response.json().then(data => ({ok: response.ok, data: data})))
            .then(result => {
                if (!result.ok || !result.data.ok) {
                    throw new Error(result.data.error || 'Note was rejected.');
                }
                clearNoteForm(payload.date);
                const count = result.data.created_count || 1;
                showMessage(count > 1 ? count + ' dispatch notes saved.' : 'Dispatch note saved.', 'success');
                calendar.refetchEvents();
                refreshCapacity(currentRangeInfo());
                refreshNotes(currentRangeInfo());
            })
            .catch(error => showMessage(error.message, 'danger'));
    });
    document.getElementById('dispatch-note-delete').addEventListener('click', function () {
        const noteId = document.getElementById('dispatch-note-id').value;
        if (!noteId) return;
        fetch(endpoint(page.dataset.noteDeleteUrlTemplate, noteId), {
            method: 'POST',
            headers: {'Content-Type': 'application/json'}
        })
            .then(response => response.json().then(data => ({ok: response.ok, data: data})))
            .then(result => {
                if (!result.ok || !result.data.ok) {
                    throw new Error(result.data.error || 'Delete was rejected.');
                }
                clearNoteForm();
                showMessage('Dispatch note deleted.', 'success');
                calendar.refetchEvents();
                refreshCapacity(currentRangeInfo());
                refreshNotes(currentRangeInfo());
            })
            .catch(error => showMessage(error.message, 'danger'));
    });
    clearNoteForm();
});
