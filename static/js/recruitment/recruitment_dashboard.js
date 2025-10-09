console.log('[Recruit] dashboard js loaded');
(async function() {
  const res = await fetch('/api/v1/recruitment/stats/overview');
  console.log('[Recruit] stats GET', res.status);
  if (!res.ok) return;
  const data = await res.json();
  console.log('[Recruit] stats payload', data);

  document.getElementById('stat-total').textContent = data.total ?? 0;

  const statusLabelsMap = {
    background_check: 'ตรวจประวัติ',
    waiting_schedule: 'รอนัดหมาย',
    scheduled: 'นัดหมายแล้ว',
    passed: 'ผ่านสัมภาษณ์',
    failed: 'ไม่ผ่าน',
    pending_result: 'รอแจ้งผล'
  };

  // Status donut
  const sKeys = Object.keys(data.by_status || {});
  const sVals = sKeys.map(k => data.by_status[k] || 0);
  new Chart(document.getElementById('chart-status'), {
    type: 'doughnut',
    data: { labels: sKeys.map(k => statusLabelsMap[k] || k), datasets: [{ data: sVals }] },
    options: { plugins: { legend: { position: 'bottom' } } }
  });

  // Source pie
  const srcKeys = Object.keys(data.by_source || {});
  const srcVals = srcKeys.map(k => data.by_source[k] || 0);
  new Chart(document.getElementById('chart-source'), {
    type: 'pie',
    data: { labels: srcKeys, datasets: [{ data: srcVals }] },
    options: { plugins: { legend: { position: 'bottom' } } }
  });

  // 30d line
  const days = data.last_30d || [];
  new Chart(document.getElementById('chart-30d'), {
    type: 'line',
    data: {
      labels: days.map(d => d.date),
      datasets: [{ label: 'ผู้สมัคร/วัน', data: days.map(d => d.count), tension: 0.2 }]
    },
    options: { scales: { y: { beginAtZero: true } } }
  });
})();
