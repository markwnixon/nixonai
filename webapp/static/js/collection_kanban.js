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
        const rateConUploadUrlTemplate = page.dataset.rateConUploadUrlTemplate;
        const packageLaunchUrl = page.dataset.packageLaunchUrl;
        const logCallUrlTemplate = page.dataset.logCallUrlTemplate;
        const jobsById = new Map();
        let activeJob = null;
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
            if (job.payment_repair_needed) {
                card.classList.add('collection-kanban-card-repair');
            }
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
                ${job.payment_repair_needed ? `<div class="collection-kanban-card-line collection-kanban-card-repair-text">Repair: expected due $${escapeHtml(job.expected_balance_due)}</div>` : ''}
                <div class="collection-kanban-card-line">Invoice: ${escapeHtml(job.invoice_date || '-')} ${job.invoice_age !== '' ? `(${escapeHtml(job.invoice_age)} days)` : ''}</div>
                ${job.status === 'needs_rate_con' ? `<div class="collection-kanban-card-line collection-kanban-card-warning">${escapeHtml(job.rate_con_status)}</div>` : ''}
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

        async function postForm(url, formData) {
            const response = await fetch(url, {
                method: 'POST',
                body: formData,
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
            activeJob = job;
            document.getElementById('collection-modal-order-id').value = job.id;
            document.getElementById('collection-kanban-modal-title').textContent = `${cardIdentity(job)} | ${job.customer || ''}`;
            document.getElementById('collection-kanban-modal-summary').innerHTML = `
                <dl>
                    <dt>Stage</dt><dd>${escapeHtml(job.status_label || '-')}</dd>
                    <dt>Customer</dt><dd>${escapeHtml(job.customer || '-')}</dd>
                    <dt>JO</dt><dd>${escapeHtml(job.jo || '-')}</dd>
                    <dt>Order</dt><dd>${escapeHtml(job.order_number || '-')}</dd>
                    <dt>Container</dt><dd>${escapeHtml(job.container || '-')}</dd>
                    <dt>Booking</dt><dd>${escapeHtml(job.booking || '-')}</dd>
                    <dt>Delivery</dt><dd>${escapeHtml(job.delivery_location || '-')}</dd>
                    <dt>Invoice</dt><dd>${escapeHtml(job.invoice || '-')}</dd>
                    <dt>Invoice Date</dt><dd>${escapeHtml(job.invoice_date || '-')} ${job.invoice_age !== '' ? `(${escapeHtml(job.invoice_age)} days)` : ''}</dd>
                    <dt>Invoice Total</dt><dd>$${escapeHtml(job.invoice_total || '0.00')}</dd>
                    <dt>Paid</dt><dd>$${escapeHtml(job.paid_amount || '0.00')}</dd>
                    <dt>Balance Due</dt><dd>$${escapeHtml(job.balance_due || '0.00')}</dd>
                    <dt>Pay Check</dt><dd>${job.payment_repair_needed ? `<span class="text-danger font-weight-bold">Repair needed. Expected due $${escapeHtml(job.expected_balance_due || '0.00')}</span>` : 'OK'}</dd>
                    <dt>Rate Con</dt><dd>${Number(job.rate_con_stage || 0) > 0 ? escapeHtml(`${job.rate_con_status}${job.rate_con_file ? ` | ${job.rate_con_file}` : ''}`) : 'Not required'}</dd>
                    <dt>RC Amount</dt><dd>${job.rate_con_amount ? `$${escapeHtml(job.rate_con_amount)}` : '-'}</dd>
                    <dt>Paid Date</dt><dd>${escapeHtml(job.paid_date || '-')}</dd>
                    <dt>Payment Ref</dt><dd>${escapeHtml(job.pay_ref || '-')}</dd>
                    <dt>Payment Method</dt><dd>${escapeHtml(job.pay_method || '-')}</dd>
                </dl>
            `;
            document.getElementById('collection-modal-rate-con-stage').value = String(job.rate_con_stage || 0);
            document.getElementById('collection-modal-rate-con-amount').value = job.rate_con_amount || '';
            const rateConUploadRow = document.getElementById('collection-rate-con-upload-row');
            const rateConFile = document.getElementById('collection-rate-con-file');
            const rateConStatus = document.getElementById('collection-rate-con-upload-status');
            const rateConViewLink = document.getElementById('collection-rate-con-view-link');
            rateConFile.value = '';
            if (Number(job.rate_con_stage || 0) > 0) {
                rateConUploadRow.classList.remove('d-none');
            } else {
                rateConUploadRow.classList.add('d-none');
            }
            rateConStatus.textContent = job.rate_con_file
                ? `Current RC: ${job.rate_con_file}`
                : 'Upload a PDF rate con for this order.';
            if (job.rate_con_view_url) {
                rateConViewLink.href = job.rate_con_view_url;
                rateConViewLink.classList.remove('d-none');
            } else {
                rateConViewLink.href = '#';
                rateConViewLink.classList.add('d-none');
            }
            document.getElementById('collection-modal-email-jp').textContent = job.emailjp || '-';
            document.getElementById('collection-modal-email-oa').textContent = job.emailoa || '-';
            document.getElementById('collection-modal-email-ap').textContent = job.emailap || '-';
            const sendPackagePanel = document.getElementById('collection-send-package-panel');
            const sendPackageTitle = document.getElementById('collection-send-package-title');
            const sendPackageHelp = document.getElementById('collection-send-package-help');
            const sendPackageButton = document.getElementById('collection-send-package-button');
            if (['completed_not_invoiced', 'ready_to_send'].includes(job.status) || job.email_mode === 'rate_con') {
                sendPackagePanel.classList.remove('d-none');
                if (job.email_mode === 'rate_con') {
                    sendPackageTitle.textContent = 'Email Rate Con Request';
                    sendPackageHelp.textContent = 'Open this job in Truck Job Manager - Money Flow - Send Package with Request Rate Con selected for review and email confirmation.';
                    sendPackageButton.textContent = 'Email Rate Con Request';
                    sendPackageButton.dataset.profile = 'Request Rate Con';
                } else {
                    sendPackageTitle.textContent = 'Send Package';
                    sendPackageHelp.textContent = 'Open this job in Truck Job Manager - Money Flow - Send Package for package review and email confirmation.';
                    sendPackageButton.textContent = 'Open Send Package';
                    sendPackageButton.dataset.profile = '';
                }
            } else {
                sendPackagePanel.classList.add('d-none');
                sendPackageButton.dataset.profile = '';
            }
            const paymentLinksVisible = ['sent_current', 'over_30', 'over_60', 'partial_paid', 'bad_debts'].includes(job.status);
            const receiveLink = document.getElementById('collection-kanban-receive-link');
            const receiveParams = new URLSearchParams({
                collection_receive_order_id: job.id,
                callfrom: 'collection_kanban'
            });
            receiveLink.href = `${packageLaunchUrl}?${receiveParams.toString()}`;
            receiveLink.classList.toggle('d-none', !paymentLinksVisible);
            document.getElementById('collection-kanban-ar-link').classList.toggle('d-none', !paymentLinksVisible);
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
        document.getElementById('collection-rate-con-upload-button').addEventListener('click', async () => {
            const jobId = document.getElementById('collection-modal-order-id').value;
            const fileInput = document.getElementById('collection-rate-con-file');
            if (!fileInput.files || !fileInput.files.length) {
                showMessage('Choose a PDF rate con to upload.', 'warning');
                return;
            }
            const formData = new FormData();
            formData.append('rate_con', fileInput.files[0]);
            formData.append('rate_con_amount', document.getElementById('collection-modal-rate-con-amount').value);
            const {response, data} = await postForm(endpoint(rateConUploadUrlTemplate, jobId), formData);
            if (!response.ok || !data.ok) {
                showMessage(data.error || 'Unable to upload rate con.', 'warning');
                return;
            }
            jobsById.set(String(jobId), data.job);
            activeJob = data.job;
            showMessage('Rate con uploaded and marked received.', 'success');
            openModal(jobId);
            loadBoard();
        });
        document.getElementById('collection-send-package-button').addEventListener('click', async () => {
            const jobId = document.getElementById('collection-modal-order-id').value;
            const profile = document.getElementById('collection-send-package-button').dataset.profile || '';
            const params = new URLSearchParams({
                collection_package_order_id: jobId,
                callfrom: 'collection_kanban'
            });
            if (profile) {
                params.set('collection_package_profile', profile);
            }
            window.location.href = `${packageLaunchUrl}?${params.toString()}`;
        });
        document.getElementById('collection-update-emails-button').addEventListener('click', async () => {
            const jobId = document.getElementById('collection-modal-order-id').value;
            const params = new URLSearchParams({
                collection_update_emails_order_id: jobId,
                callfrom: 'collection_kanban'
            });
            window.location.href = `${packageLaunchUrl}?${params.toString()}`;
        });
        document.getElementById('collection-kanban-form').addEventListener('submit', async (event) => {
            event.preventDefault();
            const jobId = document.getElementById('collection-modal-order-id').value;
            const payload = {
                rate_con_stage: document.getElementById('collection-modal-rate-con-stage').value,
                rate_con_amount: document.getElementById('collection-modal-rate-con-amount').value,
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
