(function () {
    function initKanbanBoard() {
    const page = document.querySelector('.dispatch-kanban-page');
    if (!page) {
        return;
    }

    const board = document.getElementById('dispatch-kanban-board');
    const message = document.getElementById('dispatch-kanban-message');
    const modal = $('#dispatch-kanban-modal');
    const pinModal = $('#dispatch-kanban-pin-modal');
    const jobsUrl = page.dataset.jobsUrl;
    const moveUrlTemplate = page.dataset.moveUrlTemplate;
    const updateUrlTemplate = page.dataset.updateUrlTemplate;
    const reviewUrlTemplate = page.dataset.reviewUrlTemplate;
    const uploadProofUrlTemplate = page.dataset.uploadProofUrlTemplate;
    const makePinOptionsUrlTemplate = page.dataset.makePinOptionsUrlTemplate;
    const makePinUrlTemplate = page.dataset.makePinUrlTemplate;
    const activatePinUrlTemplate = page.dataset.activatePinUrlTemplate;
    const deletePinUrlTemplate = page.dataset.deletePinUrlTemplate;
    const jobsById = new Map();
    const pinCandidatesById = new Map();
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

    function releaseLine(job) {
        if (!job.release) {
            return '';
        }
        const label = job.is_import ? 'BOL' : 'Booking';
        return `<div class="dispatch-kanban-card-line">${label}: ${escapeHtml(job.release)}</div>`;
    }

    function renderCard(job) {
        if (job.item_type === 'pin_pairing') {
            return renderPinPairingCard(job);
        }
        const card = document.createElement('div');
        card.className = 'dispatch-kanban-card';
        if (job.drop_pick_pulled) {
            card.classList.add('dispatch-kanban-card-dp-pulled');
        }
        card.dataset.id = job.id;
        card.dataset.status = job.workflow_status;
        if (job.workflow_status === 'new_orders') {
            card.innerHTML = `
                <div class="dispatch-kanban-card-title">${escapeHtml(cardTitle(job))}</div>
                <div class="dispatch-kanban-card-line">${escapeHtml(job.customer || job.shipper || 'No customer')}</div>
                <div class="dispatch-kanban-card-line">${escapeHtml(job.delivery_location || 'No delivery address')}</div>
                ${releaseLine(job)}
                <div class="dispatch-kanban-card-line">Ship Arrives: ${escapeHtml(job.ship_arrive_date || '-')}</div>
                <div class="dispatch-kanban-card-line">Anticipated Pull: ${escapeHtml(job.pull_date || '-')}</div>
                <div class="dispatch-kanban-card-line">LFD: ${escapeHtml(job.last_free_day || '-')}</div>
            `;
            card.addEventListener('click', () => openModal(job.id));
            return card;
        }
        const dateLine = job.hold_status
            ? `LFD: ${escapeHtml(job.last_free_day || '-')}`
            : `Delivery: ${escapeHtml(job.scheduled_delivery_date || job.required_delivery_date || '-')} ${escapeHtml(job.scheduled_delivery_time || '')}`;
        const dropPickAlert = job.workflow_status === 'drop_pick' && job.is_export
            ? (job.drop_pick_pulled ? 'Load-In' : 'Empty-Out')
            : '';
        card.innerHTML = `
            <div class="dispatch-kanban-card-title">${escapeHtml(cardTitle(job))}</div>
            <div class="dispatch-kanban-card-line">${escapeHtml(job.customer || job.shipper || 'No customer')}</div>
            <div class="dispatch-kanban-card-line dispatch-kanban-card-muted">${escapeHtml([job.steamship_line, job.container_type].filter(Boolean).join(' | ') || 'No steamship line')}</div>
            <div class="dispatch-kanban-card-line">${escapeHtml(job.delivery_location || 'No delivery location')}</div>
            ${releaseLine(job)}
            ${job.hold_status ? `<div class="dispatch-kanban-card-line dispatch-kanban-card-warning">${escapeHtml(job.hold_status)}</div>` : ''}
            ${dropPickAlert ? `<div class="dispatch-kanban-card-line dispatch-kanban-card-warning">${escapeHtml(dropPickAlert)}</div>` : ''}
            ${job.delivered_alert ? `<div class="dispatch-kanban-card-line dispatch-kanban-card-warning">${escapeHtml(job.delivered_message || 'Delivered')}</div>` : ''}
            ${job.pull_today_alert ? `<div class="dispatch-kanban-card-line dispatch-kanban-card-warning">${escapeHtml(job.pull_today_message || 'Pull Today')}</div>` : ''}
            ${job.placeholder_delivery_date_alert && job.workflow_status !== 'drop_pick' ? `<div class="dispatch-kanban-card-line dispatch-kanban-card-warning">${escapeHtml(job.placeholder_delivery_date_message || 'Update Placeholder Delivery Date')}</div>` : ''}
            <div class="dispatch-kanban-card-line">${dateLine}</div>
            ${job.hold_status ? '' : `<div class="dispatch-kanban-card-line">Pull: ${escapeHtml(job.pull_date || '-')} | Return: ${escapeHtml(job.return_date || '-')}</div>`}
        `;
        card.addEventListener('click', () => openModal(job.id));
        return card;
    }

    function renderPinPairingCard(pin) {
        const card = document.createElement('div');
        card.className = 'dispatch-kanban-card dispatch-kanban-pin-card';
        card.dataset.id = pin.id;
        card.dataset.pinId = pin.pin_id;
        card.dataset.status = 'pin_assigned';
        card.innerHTML = `
            <div class="dispatch-kanban-card-title">${escapeHtml(pin.timeslot || 'No time')} | ${escapeHtml(pin.driver || 'No driver')}</div>
            <div class="dispatch-kanban-card-line">${escapeHtml(pin.truck || 'No truck')}${pin.tag ? ` | ${escapeHtml(pin.tag)}` : ''}</div>
            <div class="dispatch-kanban-card-line dispatch-kanban-card-muted">${escapeHtml(pin.pin_date || '')} | ${escapeHtml(pin.status_label || 'Pending')}</div>
            <div class="dispatch-kanban-card-line">${escapeHtml(pin.in_text || 'No in move')}</div>
            <div class="dispatch-kanban-card-line">${escapeHtml(pin.out_text || 'No out move')}</div>
            ${pin.notes ? `<div class="dispatch-kanban-card-line dispatch-kanban-card-muted">${escapeHtml(pin.notes)}</div>` : ''}
            <div class="dispatch-kanban-card-actions mt-2">
                ${pin.active ? '' : '<button type="button" class="btn btn-sm btn-outline-success kanban-pin-activate">Activate</button>'}
                <button type="button" class="btn btn-sm btn-outline-secondary kanban-pin-copy">Copy Dispatch</button>
                <button type="button" class="btn btn-sm btn-outline-danger kanban-pin-delete">Delete</button>
            </div>
        `;
        card.querySelector('.kanban-pin-activate')?.addEventListener('click', () => activatePin(pin.pin_id));
        card.querySelector('.kanban-pin-copy').addEventListener('click', () => copyDispatchText(pin.dispatch_text || ''));
        card.querySelector('.kanban-pin-delete').addEventListener('click', () => deletePin(pin.pin_id));
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

            if (window.Sortable && column.key !== 'pin_assigned') {
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

    async function activatePin(pinId) {
        const {response, data} = await postJson(endpoint(activatePinUrlTemplate, pinId), {});
        if (!response.ok || !data.ok) {
            showMessage(data.error || 'Unable to activate pin.', 'warning');
            return;
        }
        showMessage(data.message || 'Pin activated.', 'success');
        loadBoard();
    }

    async function deletePin(pinId) {
        if (!window.confirm('Delete this pin assignment?')) {
            return;
        }
        const {response, data} = await postJson(endpoint(deletePinUrlTemplate, pinId), {});
        if (!response.ok || !data.ok) {
            showMessage(data.error || 'Unable to delete pin assignment.', 'warning');
            return;
        }
        showMessage(data.message || 'Pin assignment deleted.', 'success');
        loadBoard();
    }

    async function copyDispatchText(text) {
        if (!text) {
            showMessage('No dispatch text available for this pin.', 'warning');
            return;
        }
        try {
            await navigator.clipboard.writeText(text);
            showMessage('Dispatch text copied.', 'success');
        } catch (error) {
            showMessage(text, 'info');
        }
    }

    function renderReviews(reviews, isImportReview, isEccesReview) {
        const target = document.getElementById('kanban-review-list');
        if (!reviews || !reviews.length) {
            target.innerHTML = '<div class="text-muted">No review history yet.</div>';
            return;
        }
        const hasEccesReview = isEccesReview || reviews.some((review) => (
            (review.review_type || '').toLowerCase().includes('ecces')
            || review.ecces_container_type
            || review.ecces_chassis
            || review.ecces_avail_terminal
            || review.ecces_gate_in
            || review.ecces_cbp_exam_complete
            || review.ecces_customs_release
            || review.ecces_freight_release
        ));
        const headers = hasEccesReview
            ? ['Review<br>Date', 'Shipline', 'Container<br>Type', 'Chassis', 'Avail<br>Terminal', 'CES<br>Gate In', 'CBP Exam<br>Complete', 'Customs<br>Release', 'Freight<br>Release']
            : (isImportReview
                ? ['Review<br>Date', 'Shipline', 'Vessel', 'Voyage', 'Arrival<br>Date', 'Equipment<br>Size', 'Location', 'Line<br>Status', 'Customs<br>Status', 'LFD']
                : ['Review<br>Date', 'Shipline', 'Vessel', 'Voyage', 'Equipment<br>Size', 'ERD', 'Cutoff']);
        const rows = reviews.map((review) => {
            const values = hasEccesReview
                ? [
                    review.review_date || review.created_at || '',
                    review.shipline || '-',
                    review.ecces_container_type || '-',
                    review.ecces_chassis || '-',
                    review.ecces_avail_terminal || '-',
                    review.ecces_gate_in || '-',
                    review.ecces_cbp_exam_complete || '-',
                    review.ecces_customs_release || '-',
                    review.ecces_freight_release || '-',
                ]
                : (isImportReview
                    ? [
                        review.review_date || review.created_at || '',
                        review.shipline || '-',
                        review.ship || '-',
                        review.voyage || '-',
                        review.arrival_date || '-',
                        review.equipment_size || '-',
                        review.location || '-',
                        review.line_status || '-',
                        review.customs_status || '-',
                        review.lfd_date || '-',
                    ]
                    : [
                        review.review_date || review.created_at || '',
                        review.shipline || '-',
                        review.ship || '-',
                        review.voyage || '-',
                        review.equipment_size || '-',
                        review.erd_date || '-',
                        review.cutoff_date || '-',
                    ]);
            return `<tr>${values.map((value) => `<td>${escapeHtml(value)}</td>`).join('')}</tr>`;
        }).join('');
        target.innerHTML = `
            <div class="dispatch-kanban-review-table-wrap">
                <table class="table table-sm table-bordered dispatch-kanban-review-table mb-0">
                    <thead>
                        <tr>
                            ${headers.map((header) => `<th>${header}</th>`).join('')}
                        </tr>
                    </thead>
                    <tbody>
                        ${rows}
                    </tbody>
                </table>
            </div>
        `;
    }

    async function loadReviews(jobId) {
        const target = document.getElementById('kanban-review-list');
        target.innerHTML = '<div class="text-muted">Loading review history...</div>';
        const response = await fetch(endpoint(reviewUrlTemplate, jobId));
        const data = await response.json();
        if (!response.ok || !data.ok) {
            target.innerHTML = '<div class="text-danger">Unable to load review history.</div>';
            return;
        }
        renderReviews(data.reviews || [], Boolean(data.is_import), Boolean(data.is_ecces_hold));
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

    function setModalGroupVisible(selector, visible) {
        document.querySelectorAll(selector).forEach((element) => {
            element.classList.toggle('d-none', !visible);
        });
    }

    function canMakePin(job) {
        return job.workflow_status === 'drop_pick' && job.is_export && job.drop_pick_pulled;
    }

    function openModal(jobId) {
        const job = jobsById.get(String(jobId));
        if (!job) {
            return;
        }
        const isPlanningReviewStatus = [
            'new_orders',
            'on_call',
            'upcoming_deliveries',
            'port_today',
            'drop_pick',
            'pin_assigned',
            'in_progress',
            'completed',
        ].includes(job.workflow_status);
        document.getElementById('kanban-modal-order-id').value = job.id;
        document.getElementById('dispatch-kanban-modal-title').textContent = cardTitle(job);
        const customerLine = [job.customer || job.shipper || '', job.container_type || ''].filter(Boolean).join(' | ');
        const vesselLine = [
            job.shipline || job.steamship_line || '',
            job.ship || '',
            job.voyage || '',
        ].filter(Boolean).join(' | ');
        const releaseLabel = job.is_import ? 'BOL' : 'Booking';
        const releaseSummaryLine = job.release
            ? `<dt>${releaseLabel}</dt><dd>${escapeHtml(job.release)}</dd>`
            : '';
        const portDateLines = job.is_import ? `
                <dt>Ship Arrives</dt><dd>${escapeHtml(job.ship_arrive_date || '-')}</dd>
                <dt>LFD</dt><dd>${escapeHtml(job.last_free_day || '-')}</dd>
        ` : `
                <dt>ERD</dt><dd>${escapeHtml(job.erd_date || '-')}</dd>
                <dt>Cutoff Date</dt><dd>${escapeHtml(job.cutoff_date || job.last_free_day || '-')}</dd>
        `;
        const summaryHtml = isPlanningReviewStatus ? `
            <dl>
                <dt>Customer|Size</dt><dd>${escapeHtml(customerLine || '-')}</dd>
                <dt>Delivery</dt><dd>${escapeHtml(job.delivery_location || '-')}</dd>
                ${releaseSummaryLine}
                <dt>SSCO|Vessel|Voyage</dt><dd>${escapeHtml(vesselLine || '-')}</dd>
                <dt>Planned Pull Date</dt><dd>${escapeHtml(job.pull_date || '-')}</dd>
                ${portDateLines}
            </dl>
        ` : `
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
                <dt>Proof</dt><dd>${job.proof_none_required ? 'No Proof Needed' : escapeHtml(job.proof || job.proof2 || job.driver_proof || '-')}</dd>
            </dl>
        `;
        document.getElementById('kanban-modal-summary').innerHTML = summaryHtml;
        setModalGroupVisible('.kanban-modal-hold-field', isPlanningReviewStatus);
        setModalGroupVisible('.kanban-modal-planned-pull-field', isPlanningReviewStatus);
        setModalGroupVisible('.kanban-modal-assignment-field', !isPlanningReviewStatus);
        setModalGroupVisible('.kanban-modal-pin-field', !isPlanningReviewStatus);
        setModalGroupVisible('.kanban-modal-billing-field', !isPlanningReviewStatus);
        const showReviewPanel = isPlanningReviewStatus;
        document.querySelector('.dispatch-kanban-review-title').textContent =
            (job.hold_status || '').toLowerCase() === 'ecces' ? 'ECCES Review Log' : 'Daily Review Log';
        document.getElementById('kanban-review-panel').classList.toggle('d-none', !showReviewPanel);
        if (showReviewPanel) {
            loadReviews(job.id);
        }
        setSelectValue('kanban-modal-status', job.workflow_status);
        setSelectValue('kanban-modal-hold-type', job.hold_status);
        document.getElementById('kanban-modal-planned-pull-date').value = job.pull_date || '';
        setSelectValue('kanban-modal-driver', job.driver);
        setSelectValue('kanban-modal-truck', job.truck);
        document.getElementById('kanban-modal-date').value = job.scheduled_delivery_date || '';
        document.getElementById('kanban-modal-time').value = job.scheduled_delivery_time || '';
        setSelectValue('kanban-modal-delivery-type', job.delivery_type);
        document.getElementById('kanban-modal-pin').value = job.pin_reference || '';
        document.getElementById('kanban-modal-billing').value = job.billing_status || '';
        document.getElementById('kanban-modal-notes').value = job.notes || '';
        document.getElementById('kanban-modal-override-pin').checked = false;
        document.getElementById('kanban-modal-no-proof-needed').checked = Boolean(job.proof_none_required);
        const showProofUpload = ['in_progress', 'completed'].includes(job.workflow_status)
            && !job.has_delivery_proof
            && !job.proof_none_required;
        document.getElementById('kanban-proof-upload-panel').classList.toggle('d-none', !showProofUpload);
        document.getElementById('kanban-proof-file').value = '';
        document.getElementById('kanban-make-pin-open').classList.toggle('d-none', !canMakePin(job));
        modal.modal('show');
    }

    function renderPinCandidateOption(candidate) {
        const parts = [
            candidate.jo,
            candidate.customer,
            candidate.container || candidate.booking,
            candidate.container_type,
            candidate.date ? `Pull ${candidate.date}` : '',
        ].filter(Boolean);
        return parts.join(' | ');
    }

    function updatePinPreview() {
        const selectedId = document.getElementById('kanban-pin-out-order').value;
        const candidate = pinCandidatesById.get(String(selectedId));
        document.getElementById('kanban-pin-preview-out').textContent = candidate ? candidate.text : '';
    }

    function fillPinSelect(id, rows, valueKey, labelFn, emptyLabel) {
        const select = document.getElementById(id);
        select.innerHTML = `<option value="">${emptyLabel}</option>`;
        (rows || []).forEach((row) => {
            const option = document.createElement('option');
            option.value = row[valueKey] || '';
            option.textContent = labelFn(row);
            select.appendChild(option);
        });
    }

    async function openMakePinModal() {
        const jobId = document.getElementById('kanban-modal-order-id').value;
        const response = await fetch(endpoint(makePinOptionsUrlTemplate, jobId));
        const data = await response.json();
        if (!response.ok || !data.ok) {
            showMessage(data.error || 'Unable to load Make Pin options.', 'warning');
            return;
        }
        pinCandidatesById.clear();
        document.getElementById('kanban-pin-in-order-id').value = jobId;
        document.getElementById('kanban-pin-date').value = data.pin_date || '';
        document.getElementById('kanban-pin-in-summary').textContent = data.in_job ? data.in_job.text : '';
        document.getElementById('kanban-pin-preview-in').textContent = data.in_job ? data.in_job.text : '';
        fillPinSelect(
            'kanban-pin-timeslot',
            (data.timeslots || []).map((slot) => ({value: slot})),
            'value',
            (row) => row.value,
            'Select time'
        );
        fillPinSelect(
            'kanban-pin-driver',
            data.drivers || [],
            'name',
            (row) => row.truck ? `${row.name} | ${row.truck}` : row.name,
            'Select driver'
        );
        fillPinSelect(
            'kanban-pin-truck',
            data.trucks || [],
            'unit',
            (row) => [row.unit, row.type, row.plate].filter(Boolean).join(' | '),
            'Select truck'
        );
        const select = document.getElementById('kanban-pin-out-order');
        select.innerHTML = '<option value="">Select available out job</option>';
        (data.candidates || []).forEach((candidate) => {
            pinCandidatesById.set(String(candidate.id), candidate);
            const option = document.createElement('option');
            option.value = candidate.id;
            option.textContent = renderPinCandidateOption(candidate);
            select.appendChild(option);
        });
        updatePinPreview();
        modal.modal('hide');
        pinModal.modal('show');
    }

    document.getElementById('dispatch-kanban-form').addEventListener('submit', async (event) => {
        event.preventDefault();
        const jobId = document.getElementById('kanban-modal-order-id').value;
        const payload = {
            workflow_status: document.getElementById('kanban-modal-status').value,
            hold_type: document.getElementById('kanban-modal-hold-type').value,
            planned_pull_date: document.getElementById('kanban-modal-planned-pull-date').value,
            driver: document.getElementById('kanban-modal-driver').value,
            truck: document.getElementById('kanban-modal-truck').value,
            scheduled_delivery_date: document.getElementById('kanban-modal-date').value,
            scheduled_delivery_time: document.getElementById('kanban-modal-time').value,
            delivery_type: document.getElementById('kanban-modal-delivery-type').value,
            pin_reference: document.getElementById('kanban-modal-pin').value,
            billing_status: document.getElementById('kanban-modal-billing').value,
            notes: document.getElementById('kanban-modal-notes').value,
            override_pin: document.getElementById('kanban-modal-override-pin').checked,
            no_proof_needed: document.getElementById('kanban-modal-no-proof-needed').checked,
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

    document.getElementById('kanban-proof-upload-button').addEventListener('click', async () => {
        const jobId = document.getElementById('kanban-modal-order-id').value;
        const fileInput = document.getElementById('kanban-proof-file');
        const file = fileInput.files && fileInput.files[0];
        if (!file) {
            showMessage('Select a proof PDF to upload.', 'warning');
            return;
        }
        if (!file.name.toLowerCase().endsWith('.pdf')) {
            showMessage('Proof upload must be a PDF file.', 'warning');
            return;
        }
        const formData = new FormData();
        formData.append('proof_pdf', file);
        const response = await fetch(endpoint(uploadProofUrlTemplate, jobId), {
            method: 'POST',
            body: formData,
        });
        const data = await response.json();
        if (!response.ok || !data.ok) {
            showMessage(data.error || 'Unable to upload proof PDF.', 'warning');
            return;
        }
        modal.modal('hide');
        showMessage('Proof PDF uploaded.', 'success');
        loadBoard();
    });

    document.getElementById('kanban-make-pin-open').addEventListener('click', openMakePinModal);

    document.getElementById('kanban-pin-out-order').addEventListener('change', updatePinPreview);

    document.getElementById('dispatch-kanban-pin-form').addEventListener('submit', async (event) => {
        event.preventDefault();
        const jobId = document.getElementById('kanban-pin-in-order-id').value;
        const payload = {
            pin_date: document.getElementById('kanban-pin-date').value,
            out_order_id: document.getElementById('kanban-pin-out-order').value,
            timeslot: document.getElementById('kanban-pin-timeslot').value,
            driver: document.getElementById('kanban-pin-driver').value,
            truck: document.getElementById('kanban-pin-truck').value,
        };
        const {response, data} = await postJson(endpoint(makePinUrlTemplate, jobId), payload);
        if (!response.ok || !data.ok) {
            showMessage(data.error || 'Unable to create pin row.', 'warning');
            return;
        }
        pinModal.modal('hide');
        showMessage(data.message || 'Pin row created.', 'success');
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
