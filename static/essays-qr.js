        // ===== 落款管理弹窗 =====
        var nameModal, nameInput, nameList;

        document.addEventListener('DOMContentLoaded', function() {
            nameModal = document.getElementById('nameModal');
            nameInput = document.getElementById('nameModalInput');
            nameList = document.getElementById('nameList');

            document.getElementById('addNameBtn').addEventListener('click', openNameModal);
            document.getElementById('closeNameModal').addEventListener('click', closeNameModal);
            nameModal.addEventListener('click', function(e) {
                if (e.target === nameModal) closeNameModal();
            });

            document.getElementById('confirmNameBtn').addEventListener('click', function() {
                var name = nameInput.value.trim();
                if (name) {
                    addCustomName(name);
                    nameInput.value = '';
                    renderNameList();
                }
            });

            nameInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    document.getElementById('confirmNameBtn').click();
                }
            });
        });

        function openNameModal() {
            nameModal.classList.add('open');
            renderNameList();
            nameInput.value = '';
            nameInput.focus();
        }

        function closeNameModal() {
            nameModal.classList.remove('open');
        }

        function renderNameList() {
            var names = getCustomNames();
            if (names.length === 0) {
                nameList.innerHTML = '<div class="name-list-empty">暂无落款，添加一个吧</div>';
                return;
            }
            nameList.innerHTML = names.map(function(name) {
                return '<div class="name-list-item">' +
                    '<span>' + name + '</span>' +
                    '<button class="name-delete-btn" onclick="deleteName(\'' + name + '\')">×</button>' +
                    '</div>';
            }).join('');
        }

        function deleteName(name) {
            var names = getCustomNames();
            var idx = names.indexOf(name);
            if (idx !== -1) {
                names.splice(idx, 1);
                saveCustomNames(names);
                renderNameList();
                renderCustomNames();
            }
        }

        function openQrModal() {
            var modal = document.getElementById('qrModal');
            modal.classList.add('open');
            fetch('/api/get_lan_ip')
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    var ip = data.ip;
                    var port = data.port;
                    var path = location.pathname + location.search;
                    var fullUrl = 'http://' + ip + ':' + port + path;
                    document.getElementById('qrUrl').textContent = fullUrl;
                    var qrDiv = document.getElementById('qrcode');
                    qrDiv.innerHTML = '';
                    if (window.qrCodeInstance) { window.qrCodeInstance.clear(); }
                    window.qrCodeInstance = new QRCode(qrDiv, {
                        text: fullUrl,
                        width: 200,
                        height: 200,
                        colorDark: '#1a1a1a',
                        colorLight: '#ffffff',
                        correctLevel: QRCode.CorrectLevel.M
                    });
                })
                .catch(function() {
                    document.getElementById('qrcode').innerHTML = '<span style="font-size:13px;color:#e05050;">获取IP失败</span>';
                });
        }
        function closeQrModal() {
            document.getElementById('qrModal').classList.remove('open');
        }
        document.getElementById('qrModal').addEventListener('click', function(e) {
            if (e.target === this) closeQrModal();
        });
