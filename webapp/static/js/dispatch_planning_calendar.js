document.addEventListener('DOMContentLoaded', function () {
    const page = document.querySelector('.dispatch-calendar-page');
    const calendarEl = document.getElementById('dispatch-calendar');
    const messageEl = document.getElementById('dispatch-calendar-message');
    const capacityEl = document.getElementById('dispatch-capacity-strip');
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
            if (item.lfd_near || item.lfd_past) div.classList.add('dispatch-capacity-lfd');
            div.innerHTML = [
                '<strong>' + item.date + '</strong>',
                '<span>' + item.scheduled + ' scheduled / ' + (item.capacity || 0) + ' capacity</span>',
                item.lfd_past ? '<div>' + item.lfd_past + ' past LFD</div>' : '',
                item.lfd_near ? '<div>' + item.lfd_near + ' near LFD</div>' : ''
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

    function eventDetailsHtml(event) {
        const p = event.extendedProps;
        const rows = [
            ['JO', p.jo],
            ['Container', p.container],
            ['Customer', p.customer],
            ['Delivery', p.delivery_location || p.delivery_city_state || p.delivery],
            ['Driver', p.driver],
            ['Truck', p.truck],
            ['Appointment', p.appointment_time],
            ['Status', p.status],
            ['Last Free Day', p.last_free_day],
            ['PIN', p.pin_status]
        ];
        return '<dl>' + rows.map(function (row) {
            return '<dt>' + row[0] + '</dt><dd>' + (row[1] || '-') + '</dd>';
        }).join('') + '</dl>';
    }

    function openEventModal(event) {
        const p = event.extendedProps;
        document.getElementById('dispatch-modal-order-id').value = event.id;
        document.getElementById('dispatch-event-modal-title').textContent = p.container || p.jo || 'Dispatch Job';
        document.getElementById('dispatch-modal-summary').innerHTML = eventDetailsHtml(event);
        document.getElementById('dispatch-modal-date').value = p.scheduled_date || event.startStr.substring(0, 10);
        document.getElementById('dispatch-modal-time').value = p.scheduled_time || '';
        document.getElementById('dispatch-modal-driver').value = p.driver || '';
        document.getElementById('dispatch-modal-truck').value = p.truck || '';
        document.getElementById('dispatch-modal-status').value = p.status || '';
        document.getElementById('dispatch-modal-notes').value = p.notes || '';
        modalEl.modal('show');
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
            const lines = [
                arg.event.title,
                p.shipper || p.customer,
                p.appointment_time ? 'Appt ' + p.appointment_time : '',
                p.last_free_day ? 'LFD ' + p.last_free_day : ''
            ].filter(Boolean);
            return {html: '<div>' + lines.map(line => '<div>' + line + '</div>').join('') + '</div>'};
        }
    });

    calendar.render();

    let filterTimer = null;
    document.querySelectorAll('.dispatch-filter').forEach(function (el) {
        el.addEventListener('change', function () {
            calendar.refetchEvents();
            refreshCapacity(currentRangeInfo());
        });
    });
    document.getElementById('dispatch-filter-search').addEventListener('input', function () {
        window.clearTimeout(filterTimer);
        filterTimer = window.setTimeout(function () {
            calendar.refetchEvents();
            refreshCapacity(currentRangeInfo());
        }, 250);
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
            notes: document.getElementById('dispatch-modal-notes').value
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
});
