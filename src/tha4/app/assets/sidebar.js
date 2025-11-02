// 공통 사이드바 토글 스크립트
// - 토글 버튼 id: #sidebar-toggle 또는 #sidebarToggle (둘 다 지원)
// - 사이드바 컨테이너 id: #sidebarContainer
// - 오버레이 id: #sidebar-overlay

document.addEventListener('DOMContentLoaded', () => {
  const container = document.getElementById('sidebarContainer');
  const overlay = document.getElementById('sidebar-overlay');
  const togglers = [
    document.getElementById('sidebar-toggle'),
    document.getElementById('sidebarToggle'),
  ].filter(Boolean);

  const OPEN = 'sidebar-open';

  function setOverlay(open) {
    if (!overlay) return;
    if (open) {
      overlay.style.display = 'block';
      requestAnimationFrame(() => { overlay.style.opacity = '1'; });
    } else {
      overlay.style.opacity = '0';
      setTimeout(() => { if (overlay) overlay.style.display = 'none'; }, 300);
    }
  }

  function toggleSidebar() {
    if (!container) return;
    const willOpen = !container.classList.contains(OPEN);
    container.classList.toggle(OPEN);
    setOverlay(willOpen);
  }

  // 초기 오버레이 상태 동기화
  if (container) setOverlay(container.classList.contains(OPEN));

  togglers.forEach((btn) => btn.addEventListener('click', toggleSidebar));
  if (overlay) overlay.addEventListener('click', toggleSidebar);
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && container && container.classList.contains(OPEN)) {
      toggleSidebar();
    }
  });
});


