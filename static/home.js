        // ===== 究极诗词引擎 2.0 =====
        document.addEventListener('DOMContentLoaded', function() {
            // --- 动态生存拷问 ---
            var hour = new Date().getHours();
            var greeting = '';
            if (hour >= 6 && hour < 12) {
                greeting = '系统重启。今天的算力，打算耗费在哪里？';
            } else if (hour >= 12 && hour < 18) {
                greeting = '进度条过半。你在创造价值，还是在制造焦虑？';
            } else if (hour >= 18 && hour < 24) {
                greeting = '夜深灯火，今夜写代码还是读诗？';
            } else {
                greeting = '只有屏幕亮着。是在追赶，还是在逃避？';
            }
            var greetingEl = document.getElementById('dynamic-greeting');
            if (greetingEl) greetingEl.textContent = greeting;

            // --- 诗词盲盒 ---
            var poetryList = [
                "春城无处不飞花，<br>寒食东风御柳斜。<br><span style='display:block; text-align:right; font-size:14px; opacity:0.5; margin-top:12px; font-family: sans-serif;'>—— 韩翃《寒食》</span>",
                "四海同寒食，<br>千秋为一人。<br><span style='display:block; text-align:right; font-size:14px; opacity:0.5; margin-top:12px; font-family: sans-serif;'>—— 卢象《寒食》</span>",
                "雨中禁火空斋冷，<br>江上流莺独坐听。<br><span style='display:block; text-align:right; font-size:14px; opacity:0.5; margin-top:12px; font-family: sans-serif;'>—— 韦应物《寒食寄京师诸弟》</span>",
                "自我来黄州，<br>已过三寒食。<br><span style='display:block; text-align:right; font-size:14px; opacity:0.5; margin-top:12px; font-family: sans-serif;'>—— 苏轼《寒食雨二首》</span>",
                "醉后不知天在水，<br>满船清梦压星河。<br><span style='display:block; text-align:right; font-size:14px; opacity:0.5; margin-top:12px; font-family: sans-serif;'>—— 唐珙《题龙阳县青草湖》</span>",
                "我见青山多妩媚，<br>料青山见我应如是。<br><span style='display:block; text-align:right; font-size:14px; opacity:0.5; margin-top:12px; font-family: sans-serif;'>—— 辛弃疾《贺新郎》</span>",
                "一点浩然气，<br>千里快哉风。<br><span style='display:block; text-align:right; font-size:14px; opacity:0.5; margin-top:12px; font-family: sans-serif;'>—— 苏轼《水调歌头》</span>",
                "疏影横斜水清浅，<br>暗香浮动月黄昏。<br><span style='display:block; text-align:right; font-size:14px; opacity:0.5; margin-top:12px; font-family: sans-serif;'>—— 林逋《山园小梅》</span>",
                "骑马倚斜桥，<br>满楼红袖招。<br><span style='display:block; text-align:right; font-size:14px; opacity:0.5; margin-top:12px; font-family: sans-serif;'>—— 韦庄《菩萨蛮》</span>",
                "满堂花醉三千客，<br>一剑霜寒十四州。<br><span style='display:block; text-align:right; font-size:14px; opacity:0.5; margin-top:12px; font-family: sans-serif;'>—— 贯休《献钱尚父》</span>",
                "衰兰送客咸阳道，<br>天若有情天亦老。<br><span style='display:block; text-align:right; font-size:14px; opacity:0.5; margin-top:12px; font-family: sans-serif;'>—— 李贺《金铜仙人辞汉歌》</span>",
                "吾不识青天高，黄地厚。<br>唯见月寒日暖，来煎人寿。<br><span style='display:block; text-align:right; font-size:14px; opacity:0.5; margin-top:12px; font-family: sans-serif;'>—— 李贺《苦昼短》</span>",
                "向河梁、回头万里，故人长绝。<br>易水萧萧西风冷，满座衣冠似雪。<br><span style='display:block; text-align:right; font-size:14px; opacity:0.5; margin-top:12px; font-family: sans-serif;'>—— 辛弃疾《贺新郎》</span>",
                "少年听雨歌楼上，红烛昏罗帐。<br>壮年听雨客舟中，江阔云低、断雁叫西风。<br>而今听雨僧庐下，鬓已星星也。<br>悲欢离合总无情，一任阶前、点滴到天明。<br><span style='display:block; text-align:right; font-size:14px; opacity:0.5; margin-top:12px; font-family: sans-serif;'>—— 蒋捷《虞美人·听雨》</span>"
            ];
            var poetryContainer = document.getElementById('poetry-container');
            if (poetryContainer) {
                var randomIndex = Math.floor(Math.random() * poetryList.length);
                poetryContainer.innerHTML = poetryList[randomIndex];
            }
        });
