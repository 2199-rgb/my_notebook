        // ===== 悬浮目录自动生成 =====
        function buildTOC() {
            var md = document.getElementById('mdContent');
            var tocNav = document.getElementById('tocNav');
            var tocToggle = document.getElementById('tocToggle');
            if (!md || !tocNav) return;

            var headings = md.querySelectorAll('h2, h3');
            if (headings.length === 0) {
                if (tocToggle) tocToggle.style.display = 'none';
                return;
            }
            if (tocToggle) tocToggle.style.display = '';

            var ulStack = [tocNav];
            tocNav.innerHTML = '';

            headings.forEach(function(h, i) {
                if (!h.id) {
                    h.id = 'toc-heading-' + i;
                }

                var level = parseInt(h.tagName.charAt(1));

                while (ulStack.length > 1 && level <= parseInt(ulStack[ulStack.length - 1].dataset.level || 1)) {
                    ulStack.pop();
                }

                var li = document.createElement('li');
                var a = document.createElement('a');
                a.href = '#' + h.id;
                a.textContent = h.textContent.replace(/<\/?[^>]+>/g, '').trim();

                if (level === 3) a.classList.add('toc-h3');

                li.appendChild(a);
                li.dataset.level = level;
                ulStack[ulStack.length - 1].appendChild(li);

                var subUl = document.createElement('ul');
                subUl.dataset.level = level;
                li.appendChild(subUl);
                ulStack.push(subUl);
            });

            tocNav.querySelectorAll('ul').forEach(function(u) {
                if (u.children.length === 0) u.remove();
            });

            // 滚动监听：用 IntersectionObserver 监听每个 h2 是否进入视口顶部区域
            var tocLinks = tocNav.querySelectorAll('a');

            function updateActiveLinkById(id) {
                tocLinks.forEach(function(l) { l.classList.remove('active'); });
                if (id) {
                    var active = tocNav.querySelector('a[href="#' + id + '"]');
                    if (active) active.classList.add('active');
                }
            }

            // 用 IntersectionObserver 替代 scroll + elementFromPoint
            headings.forEach(function(h) {
                var obs = new IntersectionObserver(function(entries) {
                    entries.forEach(function(entry) {
                        if (entry.isIntersecting) {
                            updateActiveLinkById(entry.target.id);
                        }
                    });
                }, { rootMargin: '-80px 0px -70% 0px', threshold: 0 });
                obs.observe(h);
            });

            // ===== TOC 平滑精确制导跳转 =====
            // 拦截所有 TOC 链接点击，用 scrollIntoView 代替原生锚点
            tocNav.addEventListener('click', function(e) {
                var link = e.target.closest('a');
                if (!link) return;
                var href = link.getAttribute('href');
                if (!href || !href.startsWith('#')) return;
                e.preventDefault(); // 阻止原生锚点跳转
                var targetId = href.slice(1);
                var target = document.getElementById(targetId);
                if (target) {
                    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    updateActiveLinkById(targetId); // 立即同步更新激活状态
                }
            });
        }

        // ===== 分类彩色哈希圆点 =====
        function getHashColor(str) {
            var colors = [
                '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4',
                '#FFEEAD', '#D4A5A5', '#9B59B6', '#3498DB',
                '#1ABC9C', '#F1C40F', '#E67E22', '#2ECC71',
                '#E74C3C', '#8E44AD', '#16A085', '#D35400'
            ];
            var hash = 0;
            for (var i = 0; i < str.length; i++) {
                hash = str.charCodeAt(i) + ((hash << 5) - hash);
                hash = hash & hash;
            }
            return colors[Math.abs(hash) % colors.length];
        }

        function colorCategoryDots() {
            var dots = document.querySelectorAll('.cat-dot[data-cat]');
            dots.forEach(function(dot) {
                var cat = dot.getAttribute('data-cat');
                if (cat && cat !== '__uncat__') {
                    dot.style.backgroundColor = getHashColor(cat);
                    dot.style.boxShadow = '0 0 5px ' + getHashColor(cat) + '55';
                } else {
                    dot.style.backgroundColor = '#888';
                }
            });
        }

        // ===== 抽屉开关 =====
        function toggleTOC() {
            var toc = document.getElementById('tocContainer');
            var overlay = document.getElementById('tocOverlay');
            toc.classList.toggle('active');
            overlay.classList.toggle('active');
            // 移动端打开时禁止背景滚动
            var isMobile = window.innerWidth <= 768;
            if (isMobile) {
                document.body.style.overflow = toc.classList.contains('active') ? 'hidden' : '';
            }
        }

        // ===== 文件上传提交 =====
        function submitUpload() {
            document.getElementById('uploadForm').submit();
        }

        document.addEventListener('DOMContentLoaded', function() {
            buildTOC();
            colorCategoryDots();
            updateDDLs();
            setInterval(updateDDLs, 60000);
            // 新建笔记后自动进入编辑模式
            if (sessionStorage.getItem('autoswitch_edit') === '1') {
                sessionStorage.removeItem('autoswitch_edit');
                var editBtn = document.getElementById('editBtn');
                if (editBtn && editBtn.style.display !== 'none') {
                    var pathMatch = location.search.match(/note=([^&]+)/);
                    if (pathMatch) {
                        enterEditMode(decodeURIComponent(pathMatch[1]));
                    }
                }
            }
            // 搜索框事件（DOMContentLoaded 时注册，此时 DOM 已就绪）
            var searchInput = document.getElementById('searchInput');
            if (searchInput) {
                searchInput.addEventListener('input', function() {
                    var q = this.value.trim();
                    clearTimeout(searchTimer);
                    if (!q) {
                        document.getElementById('searchResults').innerHTML = '<div class="search-empty">输入关键词开始搜索</div>';
                        return;
                    }
                    document.getElementById('searchResults').innerHTML = '<div class="search-loading">搜索中…</div>';
                    searchTimer = setTimeout(function() {
                        fetch('/api/search?q=' + encodeURIComponent(q))
                            .then(function(r) { return r.json(); })
                            .then(function(data) {
                                var results = data.results || [];
                                var el = document.getElementById('searchResults');
                                if (results.length === 0) {
                                    el.innerHTML = '<div class="search-empty">没有找到相关笔记</div>';
                                    return;
                                }
                                el.innerHTML = results.map(function(r) {
                                    var safeSnippet = escapeHtml(r.snippet)
                                        .replace(/&lt;mark&gt;/g, '<mark>')
                                        .replace(/&lt;\/mark&gt;/g, '</mark>');
                                    return '<a href="/notes?note=' + encodeURIComponent(r.path) + '" ' +
                                           'class="search-result-item" onclick="closeSearchModal()">' +
                                           '<div class="search-result-cat">' + escapeHtml(r.category) + '</div>' +
                                           '<div class="search-result-title">' + escapeHtml(r.title) + '</div>' +
                                           '<div class="search-result-snippet">' + safeSnippet + '</div></a>';
                                }).join('');
                            })
                            .catch(function() {
                                document.getElementById('searchResults').innerHTML = '<div class="search-empty">搜索失败，请重试</div>';
                            });
                    }, 300);
                });
                searchInput.addEventListener('keydown', function(e) {
                    if (e.key === 'Escape') closeSearchModal();
                });
            }
        });

        function escapeHtml(str) {
            var div = document.createElement('div');
            div.textContent = str;
            return div.innerHTML;
        }

        // ===== 删除确认拦截（真正防止误删） =====
        document.querySelectorAll('.btn-delete').forEach(function(btn) {
            btn.addEventListener('click', function(event) {
                event.preventDefault();
                var form = this.closest('form');
                if (!form) return;
                if (!confirm('确定把这篇笔记移入回收站吗？')) return;
                form.submit();
            });
        });

        document.querySelectorAll('.cat-del-form').forEach(function(form) {
            form.addEventListener('submit', function(event) {
                event.preventDefault();
                if (!confirm('确定把该分类和其中的笔记移入回收站吗？')) return;
                this.submit();
            });
        });

        document.querySelectorAll('.ddl-del-btn').forEach(function(btn) {
            btn.addEventListener('click', function(event) {
                event.preventDefault();
                var form = this.closest('form');
                if (!form) return;
                if (!confirm('确定删除此 DDL？')) return;
                form.submit();
            });
        });

        // ===== 禅定模式 =====
        function toggleZen() {
            document.body.classList.toggle('zen-mode');
        }

        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && document.body.classList.contains('zen-mode')) {
                document.body.classList.remove('zen-mode');
            }
        });

        // ===== Markdown 在线编辑 =====
        function enterEditMode(path) {
            fetch('/api/get_raw_md?path=' + encodeURIComponent(path))
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    if (data.error) {
                        alert('读取失败：' + data.error);
                        return;
                    }
                    document.getElementById('mdWrapper').style.display = 'none';
                    var editorWrap = document.getElementById('editorWrap');
                    var editor = document.getElementById('mdEditor');
                    editor.value = data.content;
                    editorWrap.style.display = '';
                    // 切换按钮
                    document.getElementById('editBtn').style.display = 'none';
                    document.getElementById('saveBtn').style.display = '';
                    document.getElementById('cancelBtn').style.display = '';
                    document.getElementById('deleteBtn').style.display = 'none';
                    editor.focus();
                })
                .catch(function(e) { alert('网络错误：' + e); });
        }

        function cancelEdit() {
            document.getElementById('editorWrap').style.display = 'none';
            document.getElementById('mdWrapper').style.display = '';
            document.getElementById('editBtn').style.display = '';
            document.getElementById('saveBtn').style.display = 'none';
            document.getElementById('cancelBtn').style.display = 'none';
            document.getElementById('deleteBtn').style.display = '';
        }

        function saveEdit(path) {
            var editor = document.getElementById('mdEditor');
            var content = editor.value;
            fetch('/api/save_md', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: path, content: content })
            })
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data.error) {
                    alert('保存失败：' + data.error);
                    return;
                }
                window.location.reload();
            })
            .catch(function(e) { alert('网络错误：' + e); });
        }

        // ===== 新建笔记弹窗 =====
        function openNewNoteModal() {
            document.getElementById('newNoteName').value = '';
            document.getElementById('newNoteModal').classList.add('open');
            document.getElementById('newNoteName').focus();
        }

        function closeNewNoteModal(e) {
            if (e && e.target !== e.currentTarget) return;
            document.getElementById('newNoteModal').classList.remove('open');
        }

        function submitNewNote() {
            var name = document.getElementById('newNoteName').value.trim();
            var cat = document.getElementById('newNoteCat').value;
            if (!name) { alert('请输入文件名'); return; }
            sessionStorage.setItem('autoswitch_edit', '1');
            var form = document.createElement('form');
            form.method = 'POST';
            form.action = '/create_md';
            var f1 = document.createElement('input'); f1.name = 'filename'; f1.value = name; form.appendChild(f1);
            var f2 = document.createElement('input'); f2.name = 'category'; f2.value = cat; form.appendChild(f2);
            document.body.appendChild(form);
            form.submit();
        }

        // ===== 新建分类弹窗 =====
        function openCategoryModal() {
            document.getElementById('catNameInput').value = '';
            document.getElementById('catModal').classList.add('open');
            document.getElementById('catNameInput').focus();
        }

        function closeCategoryModal(e) {
            if (e && e.target !== e.currentTarget) return;
            document.getElementById('catModal').classList.remove('open');
        }

        function submitCategory() {
            var name = document.getElementById('catNameInput').value.trim();
            if (!name) { alert('请输入分类名称'); return; }
            var form = document.createElement('form');
            form.method = 'POST';
            form.action = '/add_category';
            var f1 = document.createElement('input'); f1.name = 'name'; f1.value = name; form.appendChild(f1);
            document.body.appendChild(form);
            form.submit();
        }

        // ===== DDL 表单展开收起 =====
        function toggleDdlForm() {
            var wrap = document.getElementById('ddlFormWrap');
            var btn = document.getElementById('ddlToggleBtn');
            wrap.classList.toggle('open');
            if (wrap.classList.contains('open')) {
                btn.textContent = '− 收起';
                wrap.querySelector('input[name="title"]').focus();
            } else {
                btn.textContent = '+ 新建';
            }
        }

        // ===== DDL 倒计时计算 =====
        function updateDDLs() {
            var items = document.querySelectorAll('.ddl-countdown');
            var now = new Date();
            now.setHours(0, 0, 0, 0);
            items.forEach(function(el) {
                var targetStr = el.dataset.target;
                if (!targetStr) return;
                var target = new Date(targetStr + 'T00:00:00');
                target.setHours(0, 0, 0, 0);
                var diff = target - now;
                var days = Math.ceil(diff / (1000 * 60 * 60 * 24));
                var parent = el.closest('.ddl-item');

                el.classList.remove('green', 'orange', 'red');
                if (parent) parent.classList.remove('urgent', 'critical');

                if (days < 0) {
                    el.textContent = '已逾期';
                    el.classList.add('red');
                    if (parent) parent.classList.add('critical');
                } else if (days === 0) {
                    el.textContent = '就是今天！';
                    el.classList.add('red');
                    if (parent) parent.classList.add('critical');
                } else if (days === 1) {
                    el.textContent = '明天';
                    el.classList.add('orange');
                    if (parent) parent.classList.add('urgent');
                } else if (days <= 3) {
                    el.textContent = days + '天';
                    el.classList.add('red');
                    if (parent) parent.classList.add('critical');
                } else if (days <= 7) {
                    el.textContent = days + '天';
                    el.classList.add('orange');
                    if (parent) parent.classList.add('urgent');
                } else {
                    el.textContent = days + '天';
                    el.classList.add('green');
                }
            });
        }

        // ===== 搜索 Modal =====
        var searchTimer = null;

        function openSearchModal() {
            document.getElementById('searchModal').classList.add('open');
            document.getElementById('searchInput').value = '';
            document.getElementById('searchResults').innerHTML = '<div class="search-empty">输入关键词开始搜索</div>';
            setTimeout(function() { document.getElementById('searchInput').focus(); }, 50);
        }

        function closeSearchModal(e) {
            if (e && e.target !== e.currentTarget) return;
            document.getElementById('searchModal').classList.remove('open');
        }
