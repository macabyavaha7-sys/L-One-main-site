# L-One Materials Service

腾讯云轻量应用服务器上的素材上传、串行转码、发布与清理服务。

## 当前架构

- API：FastAPI，仅监听 `127.0.0.1:8010`
- 队列：SQLite 持久化任务表，单 worker 串行处理
- 转码：FFmpeg
- Web：Nginx
- 状态目录：`/var/lib/l-one-materials`
- 公开目录：`/www/l-one-static/materials`
- 服务源码：`/opt/l-one-materials`

上传视频后生成：

- `video.mp4`：H.264，最长边 1280，AAC 96 kbps
- `thumbnail.webp`：最长边 640
- `preview.webm`：从第 1 秒开始的 4 秒 VP9 静音预览，最长边 640
- `metadata.json`

转码成功后，临时原文件自动删除，`data/assets.json` 自动重建。

## 安全边界

- `/api/health` 可公开访问。
- `/materials/data/assets.json` 和 `/materials/assets/` 可公开读取。
- `/admin/` 和 `/api/admin/` 由 Nginx 限定为服务器本机访问。
- 管理 API 额外要求 `X-L-One-Admin-Token`。
- 当前通过 SSH 端口转发访问管理页：`127.0.0.1:8011 -> 服务器 127.0.0.1:80`。
- 管理令牌只保存在服务器环境文件和 D 盘本地凭据文件，不写入仓库。

## 服务管理

```bash
sudo systemctl status l-one-materials-api
sudo systemctl status l-one-materials-worker
sudo systemctl status l-one-materials-cleanup.timer
sudo journalctl -u l-one-materials-api -f
sudo journalctl -u l-one-materials-worker -f
```

清理定时器每天删除超过 24 小时的遗留上传或处理中间文件。

## 主站接入条件

主站由 HTTPS 提供服务。正式接入需先让 `static.l-one.asia` 指向该服务器并配置 HTTPS，随后更新：

```json
{
  "manifestUrl": "https://static.l-one.asia/materials/data/assets.json",
  "mediaBaseUrl": "https://static.l-one.asia/materials/",
  "uploadUrl": "https://static.l-one.asia/admin/"
}
```

域名和证书就绪前，不应把 HTTP IP 写入线上主站配置，否则浏览器会阻止混合内容请求。
