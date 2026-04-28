        var qrInstance = null;
        function openQrModal() {
            document.getElementById('qrModal').classList.add('open');
            // 获取当前 LAN IP 并生成二维码
            fetch('/api/get_lan_ip')
                .then(function(r) { return r.json(); })
                .then(function(data) {
                    var ip = data.ip;
                    var port = data.port;
                    // 获取当前页面路径（笔记区的 note 参数等）
                    var path = location.pathname + location.search;
                    var fullUrl = 'http://' + ip + ':' + port + path;
                    document.getElementById('qrUrl').textContent = fullUrl;
                    // 生成二维码
                    var qrDiv = document.getElementById('qrcode');
                    qrDiv.innerHTML = '';
                    if (qrInstance) { qrInstance.clear(); qrInstance = null; }
                    qrInstance = new QRCode(qrDiv, {
                        text: fullUrl,
                        width: 200,
                        height: 200,
                        colorDark: '#1a1a1a',
                        colorLight: '#ffffff',
                        correctLevel: QRCode.CorrectLevel.M
                    });
                })
                .catch(function() {
                    document.getElementById('qrcode').innerHTML = '<span style="font-size:13px;color:var(--danger);">获取IP失败</span>';
                });
        }
        function closeQrModal(e) {
            if (e && e.target !== e.currentTarget) return;
            document.getElementById('qrModal').classList.remove('open');
        }
