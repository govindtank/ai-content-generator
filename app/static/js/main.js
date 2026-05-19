(function () {
  const toasts = document.getElementById('toast-container');
  if (!toasts) {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:1000;display:flex;flex-direction:column;gap:8px;';
    document.body.appendChild(container);
  }

  window.showToast = function (message, type) {
    type = type || 'info';
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.textContent = message;
    toast.style.cssText = `
      padding:12px 20px;
      border-radius:8px;
      font-size:0.9rem;
      font-weight:500;
      animation:slideUp 300ms ease;
      box-shadow:0 4px 16px rgba(0,0,0,0.3);
      color:white;
      background: ${type === 'error' ? '#ef4444' : type === 'success' ? '#22c55e' : '#1e293b'};
      border: 1px solid ${type === 'error' ? 'rgba(239,68,68,0.4)' : type === 'success' ? 'rgba(34,197,94,0.4)' : 'rgba(255,255,255,0.1)'};
    `;
    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transition = 'opacity 300ms ease';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  };
})();

const style = document.createElement('style');
style.textContent = `
  @keyframes slideUp {
    from { opacity: 0; transform: translateY(12px); }
    to { opacity: 1; transform: translateY(0); }
  }
`;
document.head.appendChild(style);
