document.addEventListener('DOMContentLoaded', function () {
    var select = document.getElementById('allocationPlotSelect');
    var canvas = document.getElementById('allocationPlotCanvas');
    var summary = document.getElementById('allocationPlotSummary');
    var errorBox = document.getElementById('allocationPlotError');
    if (!select || !canvas) {
        return;
    }

    function money(value) {
        return '$' + Number(value || 0).toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    function resizeCanvas() {
        var rect = canvas.getBoundingClientRect();
        var ratio = window.devicePixelRatio || 1;
        var width = Math.max(rect.width || canvas.parentElement.clientWidth || 600, 300);
        var height = 220;
        canvas.width = Math.floor(width * ratio);
        canvas.height = Math.floor(height * ratio);
        canvas.style.height = height + 'px';
        var ctx = canvas.getContext('2d');
        ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
        return {ctx: ctx, width: width, height: height};
    }

    function drawEmpty(message) {
        var plot = resizeCanvas();
        plot.ctx.clearRect(0, 0, plot.width, plot.height);
        plot.ctx.fillStyle = '#6c757d';
        plot.ctx.font = '14px sans-serif';
        plot.ctx.fillText(message || 'No allocation selected.', 16, 34);
    }

    var colors = ['#2563eb', '#dc2626', '#059669', '#7c3aed', '#ea580c', '#0891b2', '#be123c', '#4b5563'];

    function drawPlot(payloads) {
        payloads = Array.isArray(payloads) ? payloads : [payloads];
        var plot = resizeCanvas();
        var ctx = plot.ctx;
        var labels = [];
        var labelSeen = {};
        payloads.forEach(function (payload) {
            (payload.points || []).forEach(function (point) {
                if (!labelSeen[point.label]) {
                    labelSeen[point.label] = true;
                    labels.push(point.label);
                }
            });
        });
        ctx.clearRect(0, 0, plot.width, plot.height);
        if (!payloads.length || !labels.length) {
            drawEmpty('No weekly allocation values found for this period.');
            return;
        }

        var left = 56;
        var right = 18;
        var top = 38;
        var bottom = 50;
        var chartWidth = plot.width - left - right;
        var chartHeight = plot.height - top - bottom;
        var maxAmount = 0;
        var hasMoneySeries = false;
        var hasCountSeries = false;
        payloads.forEach(function (payload) {
            if (payload.is_count) {
                hasCountSeries = true;
            } else {
                hasMoneySeries = true;
            }
            (payload.points || []).forEach(function (point) {
                maxAmount = Math.max(maxAmount, Math.abs(point.amount_value || 0));
            });
        });
        if (!maxAmount) {
            maxAmount = 1;
        }

        ctx.strokeStyle = '#dee2e6';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(left, top);
        ctx.lineTo(left, top + chartHeight);
        ctx.lineTo(left + chartWidth, top + chartHeight);
        ctx.stroke();

        ctx.fillStyle = '#6c757d';
        ctx.font = '11px sans-serif';
        ctx.textAlign = 'right';
        for (var i = 0; i <= 4; i += 1) {
            var y = top + chartHeight - (chartHeight * i / 4);
            var amount = maxAmount * i / 4;
            ctx.strokeStyle = '#eef0f2';
            ctx.beginPath();
            ctx.moveTo(left, y);
            ctx.lineTo(left + chartWidth, y);
            ctx.stroke();
            ctx.fillText(hasMoneySeries && !hasCountSeries ? money(amount) : Number(amount || 0).toLocaleString(), left - 8, y + 4);
        }

        var groupWidth = chartWidth / labels.length;
        var groupGap = Math.min(10, groupWidth * 0.18);
        var usableGroupWidth = Math.max(groupWidth - groupGap, 4);
        var barWidth = Math.max(2, usableGroupWidth / payloads.length);
        ctx.textAlign = 'center';
        labels.forEach(function (label, labelIndex) {
            var groupX = left + groupWidth * labelIndex + groupGap / 2;
            payloads.forEach(function (payload, payloadIndex) {
                var pointMap = {};
                (payload.points || []).forEach(function (point) {
                    pointMap[point.label] = point;
                });
                var point = pointMap[label] || {};
                var value = Math.abs(point.amount_value || 0);
                var barHeight = chartHeight * value / maxAmount;
                var y = top + chartHeight - barHeight;
                var x = groupX + barWidth * payloadIndex;
                ctx.fillStyle = colors[payloadIndex % colors.length];
                ctx.fillRect(x, y, Math.max(barWidth - 1, 1), barHeight);
            });
            ctx.fillStyle = '#495057';
            ctx.save();
            ctx.translate(groupX + usableGroupWidth / 2, top + chartHeight + 32);
            ctx.rotate(-Math.PI / 5);
            ctx.fillText(label || '', 0, 0);
            ctx.restore();
        });

        ctx.textAlign = 'left';
        ctx.font = '11px sans-serif';
        payloads.forEach(function (payload, index) {
            var legendX = left + index * 150;
            var legendY = 16;
            ctx.fillStyle = colors[index % colors.length];
            ctx.fillRect(legendX, legendY - 9, 10, 10);
            ctx.fillStyle = '#374151';
            ctx.fillText(payload.account || 'Series ' + (index + 1), legendX + 14, legendY);
        });
    }

    function loadPlot() {
        var selectedValues = Array.prototype.slice.call(select.selectedOptions || [])
            .map(function (option) { return option.value; })
            .filter(Boolean);
        errorBox.textContent = '';
        if (!selectedValues.length) {
            summary.textContent = 'Select one or more rows to compare weekly amounts.';
            drawEmpty();
            return;
        }
        Promise.all(selectedValues.map(function (value) {
            var parts = value.split(':');
            var params = new URLSearchParams({
                company: select.getAttribute('data-company') || '',
                date_from: select.getAttribute('data-date-from') || '',
                date_to: select.getAttribute('data-date-to') || '',
                division: select.getAttribute('data-division') || 'all',
                allocation_type: parts[0],
                allocation_id: parts[1]
            });
            return fetch(select.getAttribute('data-url') + '?' + params.toString(), {
                credentials: 'same-origin'
            }).then(function (response) {
                return response.json().then(function (payload) {
                    if (!response.ok) {
                        throw new Error(payload.error || 'Unable to load allocation plot.');
                    }
                    return payload;
                });
            });
        })).then(function (payloads) {
            summary.textContent = payloads.map(function (payload) {
                return payload.account + ' ' + (payload.is_count ? Number(payload.amount || 0).toLocaleString() : payload.amount);
            }).join(' | ');
            drawPlot(payloads);
        }).catch(function (error) {
            errorBox.textContent = error.message;
            drawEmpty('Allocation plot could not be loaded.');
        });
    }

    select.addEventListener('change', loadPlot);
    window.addEventListener('resize', function () {
        if ((select.selectedOptions || []).length) {
            loadPlot();
        } else {
            drawEmpty();
        }
    });
    drawEmpty();
});
