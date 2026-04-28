document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('[data-reply-toggle]').forEach(function(btn) {
        btn.addEventListener('click', function() {
            var id = btn.getAttribute('data-reply-toggle');
            var form = document.getElementById('reply-form-' + id);
            if (!form) return;
            var open = form.classList.toggle('open');
            if (open) {
                var textarea = form.querySelector('textarea');
                if (textarea) textarea.focus();
            }
        });
    });
});
