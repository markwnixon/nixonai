document.addEventListener('DOMContentLoaded', function () {
    const page = document.querySelector('.admin-calendar-page');
    const calendarEl = document.getElementById('admin-payroll-calendar');
    if (!page || !calendarEl || typeof FullCalendar === 'undefined') {
        return;
    }

    let events = [];
    try {
        events = JSON.parse(page.dataset.events || '[]');
    } catch (error) {
        events = [];
    }

    const calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        initialDate: page.dataset.initialDate,
        height: 'auto',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,listMonth'
        },
        events: events,
        eventClick: function (info) {
            const rowId = info.event.extendedProps.row_id;
            if (!rowId) {
                return;
            }
            const row = document.getElementById('payroll-row-' + rowId);
            if (row) {
                row.scrollIntoView({behavior: 'smooth', block: 'center'});
                row.classList.add('admin-calendar-row-focus');
                window.setTimeout(function () {
                    row.classList.remove('admin-calendar-row-focus');
                }, 1800);
            }
        },
        eventContent: function (arg) {
            const props = arg.event.extendedProps;
            if (props.event_type === 'holiday') {
                return {html: '<div class="admin-calendar-event-driver">' + arg.event.title + '</div>'};
            }
            const prefix = props.event_type === 'run' ? 'Run' : 'Pay';
            const warning = props.holiday_warning ? '<div class="admin-calendar-event-warning">' + props.holiday_name + ' week</div>' : '';
            return {
                html: [
                    '<div class="admin-calendar-event-driver">' + prefix + ': ' + (props.driver || arg.event.title) + '</div>',
                    '<div>Gross ' + (props.gross || '$0.00') + '</div>',
                    '<div>Net ' + (props.net || '$0.00') + '</div>',
                    warning
                ].join('')
            };
        }
    });
    calendar.render();
});
