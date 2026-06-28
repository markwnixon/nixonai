(function () {
    function initKanbanBoard() {
    const page = document.querySelector('.dispatch-kanban-page');
    if (!page) {
        return;
    }

    const board = document.getElementById('dispatch-kanban-board');
    const message = document.getElementById('dispatch-kanban-message');
    const modal = $('#dispatch-kanban-modal');
    const jobsUrl = page.dataset.jobsUrl;
    const moveUrlTemplate = page.dataset.moveUrlTemplate;
    const updateUrlTemplate = page.dataset.updateUrlTemplate;
    const jobsById = new Map();
    let columns = [];

    function showMessage(text, type) {
        message.textContent = text;
        message.className = `alert alert-${type || 'info'} mb-0 py-2`;
        setTimeout(() => {
            message.classList.add('d-none');
        }, 4500);
    }

    function escapeHtml(value) {
        return String(value || '').replace(/[&<>"']/g, (char) => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#39;',
        }[char]));
    }

    function endpoint(template, id) {
        return template.replace('/0/', `/${id}/`);
    }

    function filterParams() {
        const params = new URLSearchParams();
        document.querySelectorAll('.kanban-filter').forEach((field) => {
            if (field.value) {
                params.set(field.id.replace('kanban-filter-', ''), field.value);
            }
        });
        return params;
    }

    function cardTitle(job) {
        const identity = job.container || job.booking || job.jo || `Order ${job.id}`;
        return `${identity}${job.delivery_city_state ? ` | ${job.delivery_city_state}` : ''}`;
    }

    function renderCard(job) {
        const card = document.createElement('div');
        card.className = 'dispatch-kanban-card';
        if (job.drop_pick_pulled) {
            card.classList.add('dispatch-kanban-card-dp-pulled');
        }
        card.dataset.id = job.id;
        card.dataset.status = job.workflow_status;
        const dateLine = job.hold_status
            ? `LFD: ${escapeHtml(job.last_free_day || '-')}`
            : `Delivery: ${escapeHtml(job.scheduled_delivery_date || job.required_delivery_date || '-')} ${escapeHtml(job.scheduled_delivery_time || '')}`;
        card.innerHTML = `
            <div class="dispatch-kanban-card-title">${escapeHtml(cardTitle(job))}</div>
            <div class="dispatch-kanban-card-line">${escapeHtml(job.customer || job.shipper || 'No customer')}</div>
            <div class="dispatch-kanban-card-line dispatch-kanban-card-muted">${escapeHtml([job.steamship_line, job.container_type].filter(Boolean).join(' | ') || 'No steamship line')}</div>
            <div class="dispatch-kanban-card-line">${escapeHtml(job.delivery_location || 'No delivery location')}</div>
            ${job.hold_status ? `<div class="dispatch-kanban-card-line dispatch-kanban-card-warning">${escapeHtml(job.hold_status)}</div>` : ''}
            <div class="dispatch-kanban-card-line">${dateLine}</div>
            ${job.hold_status ? '' : `<div class="dispatch-kanban-card-line">Pull: ${escapeHtml(job.pull_date || '-')} | Return: ${escapeHtml(job.return_date || '-')}</div>`}
        `;
        card.addEventListener('click', () => openModal(job.id));
        return card;
    }

    function renderBoard(data) {
        columns = data.columns || [];
        jobsById.clear();
        board.innerHTML = '';
        let jobCount = 0;
        columns.forEach((column) => {
            jobCount += (column.jobs || []).length;
            const columnEl = document.createElement('section');
            columnEl.className = 'dispatch-kanban-column';
            columnEl.innerHTML = `
                <div class="dispatch-kanban-column-header">
                    <span>${escapeHtml(column.label)}</span>
                    <span class="badge badge-secondary">${(column.jobs || []).length}</span>
                </div>
                <div class="dispatch-kanban-list" data-status="${escapeHtml(column.key)}"></div>
            `;
            const list = columnEl.querySelector('.dispatch-kanban-list');
            (column.jobs || []).forEach((job) => {
                jobsById.set(String(job.id), job);
                list.appendChild(renderCard(job));
            });
            board.appendChild(columnEl);

            if (window.Sortable) {
                new Sortable(list, {
                    group: 'dispatch-kanban',
                    animation: 150,
                    ghostClass: 'sortable-ghost',
                    onEnd: handleDrop,
                });
            }
        });
        if (!window.Sortable) {
            showMessage('Kanban cards loaded. Drag/drop is disabled because SortableJS did not load.', 'warning');
        }
        if (jobCount === 0) {
            showMessage(`No active dispatch jobs matched the current filters. API returned ${data.total_jobs || 0} jobs.`, 'info');
        }
    }

    async function loadBoard() {
        const params = filterParams();
        board.innerHTML = '<div class="text-muted p-3">Loading dispatch jobs...</div>';
        let response;
        try {
            response = await fetch(`${jobsUrl}?${params.toString()}`);
        } catch (error) {
            board.innerHTML = '';
            showMessage('Unable to load Kanban jobs.', 'danger');
            return;
        }
        if (!response.ok) {
            board.innerHTML = '';
            showMessage(`Unable to load Kanban jobs (${response.status}).`, 'danger');
            return;
        }
        try {
            renderBoard(await response.json());
        } catch (error) {
            board.innerHTML = '';
            showMessage('Kanban jobs loaded, but the board could not render.', 'danger');
        }
    }

    async function postJson(url, payload) {
        const response = await fetch(url, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload),
        });
        const data = await response.json();
        return {response, data};
    }

    async function handleDrop(event) {
        const card = event.item;
        const jobId = card.dataset.id;
        const newStatus = event.to.dataset.status;
        const oldStatus = event.from.dataset.status;
        if (newStatus === oldStatus) {
            return;
        }
        const {response, data} = await postJson(endpoint(moveUrlTemplate, jobId), {
            workflow_status: newStatus,
            reason: 'Kanban drag/drop',
        });
        if (!response.ok || !data.ok) {
            event.from.insertBefore(card, event.from.children[event.oldIndex] || null);
            showMessage(data.error || 'Workflow move was rejected.', 'warning');
            return;
        }
        showMessage('Workflow status updated.', 'success');
        loadBoard();
    }

    function setSelectValue(id, value) {
        const field = document.getElementById(id);
        field.value = value || '';
    }

    function openModal(jobId) {
        const job = jobsById.get(String(jobId));
        if (!job) {
            return;
        }
        document.getElementById('kanban-modal-order-id').value = job.id;
        document.getElementById('dispatch-kanban-modal-title').textContent = cardTitle(job);
        document.getElementById('kanban-modal-summary').innerHTML = `
            <dl>
                <dt>Customer</dt><dd>${escapeHtml(job.customer || job.shipper || '-')}</dd>
                <dt>Terminal</dt><dd>${escapeHtml(job.pickup_terminal || '-')}</dd>
                <dt>Delivery</dt><dd>${escapeHtml(job.delivery_location || job.delivery_city_state || '-')}</dd>
                <dt>Delivery</dt><dd>${escapeHtml(job.scheduled_delivery_date || job.required_delivery_date || '-')} ${escapeHtml(job.scheduled_delivery_time || '')}</dd>
                <dt>Pull</dt><dd>${escapeHtml(job.pull_date || '-')}</dd>
                <dt>Return</dt><dd>${escapeHtml(job.return_date || '-')}</dd>
                <dt>Ship Arrive</dt><dd>${escapeHtml(job.ship_arrive_date || '-')}</dd>
                <dt>Due Back</dt><dd>${escapeHtml(job.due_back_date || '-')}</dd>
                <dt>Last Free Day</dt><dd>${escapeHtml(job.last_free_day || '-')}</dd>
                <dt>Hold/Exam</dt><dd>${escapeHtml(job.hold_status || '-')}</dd>
                <dt>PIN</dt><dd>${escapeHtml(job.pin_status || '-')}</dd>
            </dl>
        `;
        setSelectValue('kanban-modal-status', job.workflow_status);
        setSelectValue('kanban-modal-driver', job.driver);
        setSelectValue('kanban-modal-truck', job.truck);
        document.getElementById('kanban-modal-date').value = job.scheduled_delivery_date || '';
        document.getElementById('kanban-modal-time').value = job.scheduled_delivery_time || '';
        document.getElementById('kanban-modal-pin').value = job.pin_reference || '';
        document.getElementById('kanban-modal-billing').value = job.billing_status || '';
        document.getElementById('kanban-modal-notes').value = job.notes || '';
        document.getElementById('kanban-modal-override-pin').checked = false;
        modal.modal('show');
    }

    document.getElementById('dispatch-kanban-form').addEventListener('submit', async (event) => {
        event.preventDefault();
        const jobId = document.getElementById('kanban-modal-order-id').value;
        const payload = {
            workflow_status: document.getElementById('kanban-modal-status').value,
            driver: document.getElementById('kanban-modal-driver').value,
            truck: document.getElementById('kanban-modal-truck').value,
            scheduled_delivery_date: document.getElementById('kanban-modal-date').value,
            scheduled_delivery_time: document.getElementById('kanban-modal-time').value,
            pin_reference: document.getElementById('kanban-modal-pin').value,
            billing_status: document.getElementById('kanban-modal-billing').value,
            notes: document.getElementById('kanban-modal-notes').value,
            override_pin: document.getElementById('kanban-modal-override-pin').checked,
        };
        const {response, data} = await postJson(endpoint(updateUrlTemplate, jobId), payload);
        if (!response.ok || !data.ok) {
            showMessage(data.error || 'Unable to save dispatch job.', 'warning');
            return;
        }
        modal.modal('hide');
        showMessage('Dispatch job saved.', 'success');
        loadBoard();
    });

    document.querySelectorAll('.kanban-filter').forEach((field) => {
        field.addEventListener('change', loadBoard);
    });

    loadBoard();

    }

    if (document.readyState === 'complete') {
        initKanbanBoard();
    } else {
        window.addEventListener('load', initKanbanBoard);
    }
}());
