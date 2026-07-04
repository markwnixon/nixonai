(function () {
    function initCollectionKanban() {
        const page = document.querySelector('.collection-kanban-page');
        if (!page) {
            return;
        }

        const board = document.getElementById('collection-kanban-board');
        const message = document.getElementById('collection-kanban-message');
        const count = document.getElementById('collection-kanban-count');
        const total = document.getElementById('collection-kanban-total');
        const modal = $('#collection-kanban-modal');
        const jobsUrl = page.dataset.jobsUrl;
        const updateUrlTemplate = page.dataset.updateUrlTemplate;
        const emailsUrlTemplate = page.dataset.emailsUrlTemplate;
        const sendEmailUrlTemplate = page.dataset.sendEmailUrlTemplate;
        const logCallUrlTemplate = page.dataset.logCallUrlTemplate;
        const jobsById = new Map();
        let searchTimer = null;

        function escapeHtml(value) {
            return String(value || '').replace(/[&<>"']/g, (char) => ({
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#39;',
            }[char]));
        }

        function showMessage(text, type) {
            message.textContent = text;
            message.className = `alert alert-${type || 'info'} mb-0 py-2`;
            setTimeout(() => {
                message.classList.add('d-none');
            }, 4500);
        }

        function filterParams() {
            const params = new URLSearchParams();
            document.querySelectorAll('.collection-filter').forEach((field) => {
                if (field.value) {
                    params.set(field.id.replace('collection-filter-', ''), field.value);
                }
            });
            return params;
        }

        function endpoint(template, id) {
            return template.replace('/0/', `/${id}/`);
        }

        function cardIdentity(job) {
            return job.container || job.booking || job.jo || `Order ${job.id}`;
        }

        function renderCard(job) {
            const card = document.createElement('div');
            card.className = 'collection-kanban-card';
            card.dataset.id = job.id;
            card.dataset.status = job.status;
            card.innerHTML = `
                <div class="collection-kanban-card-title">
                    <span>${escapeHtml(cardIdentity(job))}</span>
                    <span>$${escapeHtml(job.balance_due)}</span>
                </div>
                <div class="collection-kanban-card-line">${escapeHtml(job.customer || 'No customer')}</div>
                <div class="collection-kanban-card-line collection-kanban-card-muted">JO ${escapeHtml(job.jo || '-')} | Inv ${escapeHtml(job.invoice || '-')}</div>
                <div class="collection-kanban-card-line">Total $${escapeHtml(job.invoice_total)} | Paid $${escapeHtml(job.paid_amount)}</div>
                <div class="collection-kanban-card-line">Invoice: ${escapeHtml(job.invoice_date || '-')} ${job.invoice_age !== '' ? `(${escapeHtml(job.invoice_age)} days)` : ''}</div>
                ${job.rate_con_needed ? `<div class="collection-kanban-card-line collection-kanban-card-warning">${escapeHtml(job.rate_con_status)}</div>` : ''}
            `;
            card.addEventListener('click', () => openModal(job.id));
            return card;
        }

        function renderBoard(data) {
            jobsById.clear();
            board.innerHTML = '';
            count.textContent = `${data.total_jobs || 0} jobs`;
            total.textContent = `$${data.total_due || '0.00'} open`;

            (data.columns || []).forEach((column) => {
                const columnEl = document.createElement('section');
                columnEl.className = 'collection-kanban-column';
                columnEl.innerHTML = `
                    <div class="collection-kanban-column-header">
                        <span>${escapeHtml(column.label)}</span>
                        <span class="badge badge-secondary">${(column.jobs || []).length}</span>
                        <span class="collection-kanban-column-total">$${escapeHtml(column.total_due || '0.00')}</span>
                    </div>
                    <div class="collection-kanban-list"></div>
                `;
                const list = columnEl.querySelector('.collection-kanban-list');
                (column.jobs || []).forEach((job) => {
                    jobsById.set(String(job.id), job);
                    list.appendChild(renderCard(job));
                });
                board.appendChild(columnEl);
            });

            if (!data.total_jobs) {
                showMessage('No receivables matched the current filters.', 'info');
            }
        }

        async function loadBoard() {
            const params = filterParams();
            board.innerHTML = '<div class="text-muted p-3">Loading collection jobs...</div>';
            let response;
            try {
                response = await fetch(`${jobsUrl}?${params.toString()}`);
            } catch (error) {
                board.innerHTML = '';
                showMessage('Unable to load collection jobs.', 'danger');
                return;
            }
            if (!response.ok) {
                board.innerHTML = '';
                showMessage(`Unable to load collection jobs (${response.status}).`, 'danger');
                return;
            }
            try {
                renderBoard(await response.json());
            } catch (error) {
                board.innerHTML = '';
                showMessage('Collection jobs loaded, but the board could not render.', 'danger');
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

        function renderEmails(emails) {
            const target = document.getElementById('collection-kanban-email-list');
            if (!emails || !emails.length) {
                target.innerHTML = '<div class="text-muted">No logged emails or calls for this job yet.</div>';
                return;
            }
            target.innerHTML = emails.map((email) => `
                <div class="collection-kanban-email-item">
                    <div class="collection-kanban-email-subject">${escapeHtml(email.subject || '(No subject)')}</div>
                    <div class="collection-kanban-email-meta">
                        ${escapeHtml(email.sent_at || '')}
                        ${email.email_type ? ` | ${escapeHtml(email.email_type)}` : ''}
                        ${email.direction ? ` | ${escapeHtml(email.direction)}` : ''}
                        ${email.from_email ? ` | By/From ${escapeHtml(email.from_email)}` : ''}
                    </div>
                    <div class="collection-kanban-email-meta">${email.direction === 'phone' ? 'Contact' : 'To'}: ${escapeHtml(email.to_emails || '-')}</div>
                    ${email.cc_emails ? `<div class="collection-kanban-email-meta">Cc: ${escapeHtml(email.cc_emails)}</div>` : ''}
                    ${email.attachment_send_name || email.attachment_name ? `<div class="collection-kanban-email-meta">Attachment: ${escapeHtml(email.attachment_send_name || email.attachment_name)}</div>` : ''}
                    ${email.body_text ? `<div class="collection-kanban-email-body">${escapeHtml(email.body_text)}</div>` : ''}
                </div>
            `).join('');
        }

        async function loadEmails(jobId) {
            const target = document.getElementById('collection-kanban-email-list');
            target.innerHTML = '<div class="text-muted">Loading email history...</div>';
            let response;
            try {
                response = await fetch(endpoint(emailsUrlTemplate, jobId));
            } catch (error) {
                target.innerHTML = '<div class="text-danger">Unable to load email history.</div>';
                return;
            }
            if (!response.ok) {
                target.innerHTML = `<div class="text-danger">Unable to load email history (${response.status}).</div>`;
                return;
            }
            const data = await response.json();
            renderEmails(data.emails || []);
        }

        function openModal(jobId) {
            const job = jobsById.get(String(jobId));
            if (!job) {
                return;
            }
            document.getElementById('collection-modal-order-id').value = job.id;
            document.getElementById('collection-kanban-modal-title').textContent = `${cardIdentity(job)} | ${job.customer || ''}`;
            document.getElementById('collection-kanban-modal-summary').innerHTML = `
                <dl>
                    <dt>Stage</dt><dd>${escapeHtml(job.status_label || '-')}</dd>
                    <dt>Customer</dt><dd>${escapeHtml(job.customer || '-')}</dd>
                    <dt>JO</dt><dd>${escapeHtml(job.jo || '-')}</dd>
                    <dt>Container</dt><dd>${escapeHtml(job.container || '-')}</dd>
                    <dt>Booking</dt><dd>${escapeHtml(job.booking || '-')}</dd>
                    <dt>Delivery</dt><dd>${escapeHtml(job.delivery_location || '-')}</dd>
                    <dt>Invoice</dt><dd>${escapeHtml(job.invoice || '-')}</dd>
                    <dt>Invoice Date</dt><dd>${escapeHtml(job.invoice_date || '-')} ${job.invoice_age !== '' ? `(${escapeHtml(job.invoice_age)} days)` : ''}</dd>
                    <dt>Invoice Total</dt><dd>$${escapeHtml(job.invoice_total || '0.00')}</dd>
                    <dt>Paid</dt><dd>$${escapeHtml(job.paid_amount || '0.00')}</dd>
                    <dt>Balance Due</dt><dd>$${escapeHtml(job.balance_due || '0.00')}</dd>
                    <dt>Rate Con</dt><dd>${job.rate_con_needed ? escapeHtml(`${job.rate_con_status}${job.rate_con_file ? ` | ${job.rate_con_file}` : ''}`) : 'Not required'}</dd>
                    <dt>Paid Date</dt><dd>${escapeHtml(job.paid_date || '-')}</dd>
                    <dt>Payment Ref</dt><dd>${escapeHtml(job.pay_ref || '-')}</dd>
                    <dt>Payment Method</dt><dd>${escapeHtml(job.pay_method || '-')}</dd>
                </dl>
            `;
            document.getElementById('collection-modal-rate-con-stage').value = String(job.rate_con_stage || 0);
            document.getElementById('collection-email-to').value = job.email_to || '';
            document.getElementById('collection-email-cc').value = job.email_cc || '';
            document.getElementById('collection-email-subject').value = `Follow up on ${job.jo || cardIdentity(job)}`;
            document.getElementById('collection-email-body').value = '';
            document.getElementById('collection-call-contact').value = job.customer || '';
            document.getElementById('collection-call-notes').value = '';
            loadEmails(job.id);
            modal.modal('show');
        }

        document.querySelectorAll('.collection-filter').forEach((field) => {
            const eventName = field.tagName === 'INPUT' ? 'input' : 'change';
            field.addEventListener(eventName, () => {
                if (field.tagName === 'INPUT') {
                    clearTimeout(searchTimer);
                    searchTimer = setTimeout(loadBoard, 250);
                } else {
                    loadBoard();
                }
            });
        });
        document.getElementById('collection-kanban-refresh').addEventListener('click', loadBoard);
        document.getElementById('collection-kanban-form').addEventListener('submit', async (event) => {
            event.preventDefault();
            const jobId = document.getElementById('collection-modal-order-id').value;
            const payload = {
                rate_con_stage: document.getElementById('collection-modal-rate-con-stage').value,
            };
            const {response, data} = await postJson(endpoint(updateUrlTemplate, jobId), payload);
            if (!response.ok || !data.ok) {
                showMessage(data.error || 'Unable to save collection item.', 'warning');
                return;
            }
            modal.modal('hide');
            showMessage('Collection item saved.', 'success');
            loadBoard();
        });
        document.getElementById('collection-email-form').addEventListener('submit', async (event) => {
            event.preventDefault();
            const jobId = document.getElementById('collection-modal-order-id').value;
            const payload = {
                to_emails: document.getElementById('collection-email-to').value,
                cc_emails: document.getElementById('collection-email-cc').value,
                subject: document.getElementById('collection-email-subject').value,
                body: document.getElementById('collection-email-body').value,
            };
            const {response, data} = await postJson(endpoint(sendEmailUrlTemplate, jobId), payload);
            if (!response.ok || !data.ok) {
                showMessage(data.error || 'Unable to send email.', 'warning');
                return;
            }
            document.getElementById('collection-email-body').value = '';
            showMessage('Email sent and logged.', 'success');
            renderEmails(data.emails || []);
        });
        document.getElementById('collection-call-form').addEventListener('submit', async (event) => {
            event.preventDefault();
            const jobId = document.getElementById('collection-modal-order-id').value;
            const payload = {
                contact: document.getElementById('collection-call-contact').value,
                notes: document.getElementById('collection-call-notes').value,
            };
            const {response, data} = await postJson(endpoint(logCallUrlTemplate, jobId), payload);
            if (!response.ok || !data.ok) {
                showMessage(data.error || 'Unable to log phone call.', 'warning');
                return;
            }
            document.getElementById('collection-call-notes').value = '';
            showMessage('Phone call logged.', 'success');
            renderEmails(data.emails || []);
        });

        loadBoard();
    }

    if (document.readyState === 'complete') {
        initCollectionKanban();
    } else {
        window.addEventListener('load', initCollectionKanban);
    }
}());
