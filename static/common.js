/**
 * 公共 JavaScript 函数
 * 寒食季知识库
 */

// ===== 暗黑模式记忆切换 =====
(function() {
    var toggleBtn = document.getElementById('themeToggle');

    // 读取记忆
    if (localStorage.getItem('theme') === 'dark') {
        document.body.classList.add('dark-mode');
        if (toggleBtn) toggleBtn.textContent = '☀️ 日间模式';
    } else {
        if (toggleBtn) toggleBtn.textContent = '🌙 暗黑模式';
    }

    // 夜间自动切换（20:00 后自动暗黑，用户手动切换后不再覆盖）
    var savedTheme = localStorage.getItem('theme');
    var manualOverride = localStorage.getItem('manualTheme');
    if (!manualOverride && !savedTheme) {
        var hour = new Date().getHours();
        if (hour >= 20 || hour < 6) {
            document.body.classList.add('dark-mode');
            if (toggleBtn) toggleBtn.textContent = '☀️ 日间模式';
        }
    }
})();

function toggleTheme() {
    var toggleBtn = document.getElementById('themeToggle');
    var isDark = document.body.classList.toggle('dark-mode');
    if (isDark) {
        if (toggleBtn) toggleBtn.textContent = '☀️ 日间模式';
        localStorage.setItem('theme', 'dark');
        localStorage.setItem('manualTheme', 'true');
    } else {
        if (toggleBtn) toggleBtn.textContent = '🌙 暗黑模式';
        localStorage.setItem('theme', 'light');
        localStorage.setItem('manualTheme', 'true');
    }
}
