# my_notebook

一个基于 Flask 的个人知识库网站，包含随笔区、Markdown/PDF 笔记区、分类管理、DDL 倒计时和全文搜索。

## 本地运行

```powershell
pip install -r requirements.txt
python app.py
```

默认访问地址：

```text
http://127.0.0.1:5001/
```

## 配置

建议复制 `.env.example` 中的配置到自己的环境变量里，至少设置：

```text
SECRET_KEY=一段足够长的随机字符串
ADMIN_PASSWORD=管理员密码
HANSHIJI_PASSWORD=寒食季署名密码
```

当前为了兼容旧版本，如果没有配置密码，程序仍会使用旧的本地默认密码。正式部署或开放到局域网前，务必设置环境变量。

如需手机或 iPad 在同一局域网访问：

```text
APP_HOST=0.0.0.0
APP_PORT=5001
```

## 数据目录

这些目录会在运行时自动创建，并且不会提交到 Git：

```text
blog.db
uploads/
static/snippet_images/
trash/
```

删除笔记或分类时，文件会移动到 `trash/时间戳/` 下，方便误删后手动恢复。

## 代码结构

```text
app.py              # Flask 应用入口：创建 app、初始化数据库、注册路由
config.py           # 路径、密码、端口、运行模式等配置
db.py               # SQLite 连接和数据库初始化
routes/             # 页面和 API 路由
  main.py           # 首页、登录、退出、局域网 IP API
  essays.py         # 随笔区
  notes.py          # 笔记区、分类、DDL、Markdown API
services/           # 可复用业务逻辑
  auth.py           # 管理员登录状态和权限装饰器
  markdown_render.py
  network.py
  note_index.py
  paths.py
  search.py
static/             # CSS 和浏览器端 JS
templates/          # Jinja 页面结构
```
