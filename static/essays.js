        function handleImgSelect(input) {
            var nameSpan = document.getElementById('imgName');
            if (input.files && input.files[0]) {
                nameSpan.textContent = '  📎 ' + input.files[0].name;
            } else {
                nameSpan.textContent = '';
            }
        }

        function enterEditMode(essayId) {
            var card = document.querySelector('.essay-card[data-id="' + essayId + '"]');
            if (card) {
                card.classList.add('editing');
                var textarea = document.getElementById('edit-textarea-' + essayId);
                if (textarea) {
                    textarea.focus();
                }
            }
        }

        function cancelEdit(essayId) {
            var card = document.querySelector('.essay-card[data-id="' + essayId + '"]');
            if (card) {
                var textarea = document.getElementById('edit-textarea-' + essayId);
                if (textarea) {
                    textarea.value = textarea.defaultValue;
                }
                card.classList.remove('editing');
            }
        }

        function saveEdit(essayId, authorName) {
            var textarea = document.getElementById('edit-textarea-' + essayId);
            var content = textarea.value.trim();
            if (!content) {
                alert('内容不能为空');
                return;
            }

            function doSave(pwd) {
                var formData = new FormData();
                formData.append('content', content);
                if (pwd) formData.append('password', pwd);

                fetch('/essays/edit/' + essayId, {
                    method: 'POST',
                    body: formData
                })
                .then(function(response) { return response.json(); })
                .then(function(data) {
                    if (data.success) {
                        var card = document.querySelector('.essay-card[data-id="' + essayId + '"]');
                        if (card) {
                            card.querySelector('.essay-content').textContent = content;
                            card.classList.remove('editing');
                        }
                    } else {
                        alert('保存失败：' + (data.error || '未知错误'));
                    }
                })
                .catch(function(error) {
                    alert('保存失败：' + error);
                });
            }

            // 寒食季的随笔需要密码验证（使用独立编辑密码框，不干扰发布/删除）
            if (authorName === '寒食季') {
                openEditPwdModal(function(pwd) {
                    if (pwd === null) return;
                    doSave(pwd);
                });
                return;
            }

            doSave(null);
        }
        // ===== Emoji 反应 =====
        var ALL_EMOJIS = [
            '❤️','😂','🔥','👍','😍','🎉','😭','🤔','👏','💯',
            '😅','🥹','😎','🤩','😤','💪','🙏','✨','🌟','💡',
            '📚','🧠','😴','☕','🍕','🎵','🎮','🏆','💔','🤯'
        ];

        function getReactions(id) {
            return JSON.parse(localStorage.getItem('reactions_' + id) || '{}');
        }
        function saveReactions(id, data) {
            localStorage.setItem('reactions_' + id, JSON.stringify(data));
        }

        function renderReactions(id) {
            var data = getReactions(id);
            var container = document.getElementById('reactions-' + id);
            if (!container) return;
            container.innerHTML = '';
            Object.keys(data).forEach(function(emoji) {
                if (!data[emoji]) return;
                var btn = document.createElement('button');
                btn.className = 'reaction-btn' + (data[emoji].mine ? ' reacted' : '');
                btn.innerHTML = emoji + ' <span class="r-count">' + data[emoji].count + '</span>';
                btn.onclick = function() { toggleReaction(id, emoji); };
                container.appendChild(btn);
            });
        }

        function toggleReaction(id, emoji) {
            var data = getReactions(id);
            if (!data[emoji]) data[emoji] = { count: 0, mine: false };
            if (data[emoji].mine) {
                data[emoji].count--;
                data[emoji].mine = false;
                if (data[emoji].count <= 0) delete data[emoji];
            } else {
                data[emoji].count++;
                data[emoji].mine = true;
            }
            saveReactions(id, data);
            renderReactions(id);
        }

        function togglePicker(id) {
            var picker = document.getElementById('picker-' + id);
            var isOpen = picker.classList.contains('open');
            document.querySelectorAll('.reaction-picker.open').forEach(function(p) { p.classList.remove('open'); });
            if (!isOpen) {
                if (!picker.dataset.built) {
                    picker.innerHTML = ALL_EMOJIS.map(function(e) {
                        return '<span class="picker-emoji" onclick="pickEmoji(' + id + ',\'' + e + '\')">' + e + '</span>';
                    }).join('');
                    picker.dataset.built = '1';
                }
                picker.classList.add('open');
            }
        }

        function pickEmoji(id, emoji) {
            toggleReaction(id, emoji);
            document.getElementById('picker-' + id).classList.remove('open');
        }

        document.addEventListener('click', function(e) {
            if (!e.target.closest('[id^="picker-wrap-"]')) {
                document.querySelectorAll('.reaction-picker.open').forEach(function(p) { p.classList.remove('open'); });
            }
        });

        document.querySelectorAll('.essay-card[data-id]').forEach(function(card) {
            renderReactions(card.dataset.id);
        });

        // ===== 作者头像颜色配置 =====
        var AVATAR_COLORS = {
            '寒食季':  ['#4a90d9', '#7c5cdb'],
            '立春':    ['#8BC34A', '#4CAF50'],
            '雨水':    ['#00BCD4', '#0097A7'],
            '惊蛰':    ['#673AB7', '#512DA8'],
            '春分':    ['#4CAF50', '#8BC34A'],
            '清明':    ['#FF9800', '#FF5722'],
            '谷雨':    ['#795548', '#5D4037'],
            '立夏':    ['#F44336', '#E91E63'],
            '小满':    ['#FF5722', '#FF9800'],
            '芒种':    ['#FFC107', '#FFB300'],
            '夏至':    ['#FFEB3B', '#FFF176'],
            '小暑':    ['#FF9800', '#FF5722'],
            '大暑':    ['#E91E63', '#9C27B0'],
            '立秋':    ['#9C27B0', '#673AB7'],
            '处暑':    ['#673AB7', '#3F51B5'],
            '白露':    ['#3F51B5', '#2196F3'],
            '秋分':    ['#00BCD4', '#009688'],
            '寒露':    ['#009688', '#00695C'],
            '霜降':    ['#607D8B', '#455A64'],
            '立冬':    ['#795548', '#3E2723'],
            '小雪':    ['#78909C', '#546E7A'],
            '大雪':    ['#90A4AE', '#B0BEC5'],
            '冬至':    ['#B0BEC5', '#ECEFF1'],
            '小寒':    ['#546E7A', '#37474F'],
            '大寒':    ['#37474F', '#263238']
        };

        // ===== 自定义名字 localStorage 操作 =====
        var CUSTOM_NAMES_KEY = 'essayCustomNames';

        function getCustomNames() {
            var stored = localStorage.getItem(CUSTOM_NAMES_KEY);
            if (stored) {
                try {
                    return JSON.parse(stored);
                } catch(e) { return []; }
            }
            return [];
        }

        function saveCustomNames(names) {
            localStorage.setItem(CUSTOM_NAMES_KEY, JSON.stringify(names));
        }

        function addCustomName(name) {
            if (!name || name.trim() === '') return;
            name = name.trim();
            var names = getCustomNames();
            if (names.indexOf(name) !== -1) return;  // 已存在
            names.push(name);
            saveCustomNames(names);
            renderCustomNames();
            // 选中新添加的名字
            document.getElementById('authorSelect').value = name;
            updateComposeAvatar(name);
        }

        function deleteCustomName(name) {
            var names = getCustomNames();
            var idx = names.indexOf(name);
            if (idx !== -1) {
                names.splice(idx, 1);
                saveCustomNames(names);
                renderCustomNames();
            }
        }

        function renderCustomNames() {
            var group = document.getElementById('customNamesGroup');
            var names = getCustomNames();
            group.innerHTML = '';
            names.forEach(function(name) {
                var opt = document.createElement('option');
                opt.value = name;
                opt.textContent = '✨ ' + name;
                group.appendChild(opt);
            });
        }

        // ===== 初始化自定义名字 =====
        document.addEventListener('DOMContentLoaded', function() {
            renderCustomNames();

            // authorSelect 切换时更新头像
            document.getElementById('authorSelect').addEventListener('change', function() {
                updateComposeAvatar(this.value);
            });
        });

        function updateComposeAvatar(author) {
            if (!author) return;
            var avatar = document.getElementById('composeAvatar');
            var colors = AVATAR_COLORS[author] || (getCustomNames().indexOf(author) !== -1 ? ['#6B8E9F', '#5D7A8A'] : ['#4a90d9', '#7c5cdb']);
            avatar.style.background = 'linear-gradient(135deg, ' + colors[0] + ', ' + colors[1] + ')';
            avatar.textContent = author[0];
        }

        function handleEssaySubmit() {
            var select = document.getElementById('authorSelect');
            var avatar = document.getElementById('composeAvatar');
            var author = select.value;

            // 更新发布框头像
            var colors = AVATAR_COLORS[author] || (getCustomNames().indexOf(author) !== -1 ? ['#6B8E9F', '#5D7A8A'] : ['#4a90d9', '#7c5cdb']);
            avatar.style.background = 'linear-gradient(135deg, ' + colors[0] + ', ' + colors[1] + ')';
            avatar.textContent = author[0];

            // 寒食季需要密码
            if (author === '寒食季') {
                openPwdModal(function(pwd) {
                    if (pwd === null) return;  // 用户取消
                    var form = select.closest('form');
                    var pwdField = document.createElement('input');
                    pwdField.type = 'hidden';
                    pwdField.name = 'password';
                    pwdField.value = pwd;
                    form.appendChild(pwdField);
                    form.submit();
                });
                return false;
            }
            return true;
        }

        // ===== 删除随笔确认 =====
        function confirmDeleteEssay(essayId, authorName) {
            if (authorName === '寒食季') {
                openDeletePwdModal(function(pwd) {
                    if (pwd === null) return;
                    document.getElementById('delete-pwd-' + essayId).value = pwd;
                    document.getElementById('delete-form-' + essayId).submit();
                });
                return false;
            }
            if (!confirm('确定删除？')) return false;
            document.getElementById('delete-form-' + essayId).submit();
            return true;
        }

        // ===== 密码 Modal 控制（发布，仅发布操作使用） =====
        var _pwdCallback = null;

        function openPwdModal(callback) {
            _pwdCallback = callback;
            var modal = document.getElementById('pwdModal');
            var input = document.getElementById('pwdInput');
            var error = document.getElementById('pwdError');
            input.value = '';
            error.textContent = '';
            modal.classList.add('open');
            setTimeout(function() { input.focus(); }, 100);
        }

        function closePwdModal(confirmed) {
            var modal = document.getElementById('pwdModal');
            var input = document.getElementById('pwdInput');
            modal.classList.remove('open');
            // 重置为发布默认文本
            document.getElementById('pwdModalTitle').textContent = '你是寒食季那我是谁？';
            document.getElementById('pwdModalSub').textContent = '快输密码，证明身份';
            document.getElementById('pwdModalConfirm').textContent = '确认发布';
            if (confirmed) {
                var pwd = input.value;
                if (!pwd.trim()) {
                    document.getElementById('pwdError').textContent = '密码不能为空';
                    return;
                }
                if (_pwdCallback) _pwdCallback(pwd);
            } else {
                if (_pwdCallback) _pwdCallback(null);
            }
            _pwdCallback = null;
        }

        // ===== 编辑随笔密码 Modal 控制（独立，与发布/删除互不干扰） =====
        var _editPwdCallback = null;

        function openEditPwdModal(callback) {
            _editPwdCallback = callback;
            var modal = document.getElementById('editPwdModal');
            var input = document.getElementById('editPwdInput');
            var error = document.getElementById('editPwdError');
            input.value = '';
            error.textContent = '';
            modal.classList.add('open');
            setTimeout(function() { input.focus(); }, 100);
        }

        function closeEditPwdModal(confirmed) {
            var modal = document.getElementById('editPwdModal');
            var input = document.getElementById('editPwdInput');
            modal.classList.remove('open');
            if (confirmed) {
                var pwd = input.value;
                if (!pwd.trim()) {
                    document.getElementById('editPwdError').textContent = '密码不能为空';
                    return;
                }
                if (_editPwdCallback) _editPwdCallback(pwd);
            } else {
                if (_editPwdCallback) _editPwdCallback(null);
            }
            _editPwdCallback = null;
        }

        // 回车确认
        document.getElementById('pwdInput').addEventListener('keydown', function(e) {
            if (e.key === 'Enter') closePwdModal(true);
        });

        // 编辑密码框回车确认
        document.getElementById('editPwdInput').addEventListener('keydown', function(e) {
            if (e.key === 'Enter') closeEditPwdModal(true);
        });

        // 点击遮罩关闭
        document.getElementById('pwdModal').addEventListener('click', function(e) {
            if (e.target === this) closePwdModal(false);
        });

        // 编辑密码框点击遮罩关闭
        document.getElementById('editPwdModal').addEventListener('click', function(e) {
            if (e.target === this) closeEditPwdModal(false);
        });

        // ===== 删除随笔密码 Modal 控制（独立，与发布/编辑互不干扰） =====
        var _deletePwdCallback = null;

        function openDeletePwdModal(callback) {
            _deletePwdCallback = callback;
            var modal = document.getElementById('deletePwdModal');
            var input = document.getElementById('deletePwdInput');
            var error = document.getElementById('deletePwdError');
            input.value = '';
            error.textContent = '';
            modal.classList.add('open');
            setTimeout(function() { input.focus(); }, 100);
        }

        function closeDeletePwdModal(confirmed) {
            var modal = document.getElementById('deletePwdModal');
            var input = document.getElementById('deletePwdInput');
            modal.classList.remove('open');
            if (confirmed) {
                var pwd = input.value;
                if (!pwd.trim()) {
                    document.getElementById('deletePwdError').textContent = '密码不能为空';
                    return;
                }
                if (_deletePwdCallback) _deletePwdCallback(pwd);
            } else {
                if (_deletePwdCallback) _deletePwdCallback(null);
            }
            _deletePwdCallback = null;
        }

        // 删除密码框回车确认
        document.getElementById('deletePwdInput').addEventListener('keydown', function(e) {
            if (e.key === 'Enter') closeDeletePwdModal(true);
        });

        // 删除密码框点击遮罩关闭
        document.getElementById('deletePwdModal').addEventListener('click', function(e) {
            if (e.target === this) closeDeletePwdModal(false);
        });

        // 初始化卡片头像颜色
        document.querySelectorAll('.essay-card[data-author]').forEach(function(card) {
            var author = card.dataset.author;
            var colors = AVATAR_COLORS[author] || ['#4a90d9', '#7c5cdb'];
            card.style.setProperty('--avatar-color1', colors[0]);
            card.style.setProperty('--avatar-color2', colors[1]);
        });
