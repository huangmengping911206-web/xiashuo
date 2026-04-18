# 🎬 视频功能设计方案（本地存储）

## 一、数据库修改

### 1.1 新增视频表

```sql
CREATE TABLE videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uploader_id INTEGER NOT NULL,           -- 上传者 ID
    filename TEXT NOT NULL,                  -- 原始文件名
    file_path TEXT NOT NULL,                 -- 本地文件路径（相对路径）
    file_type TEXT DEFAULT 'video/mp4',      -- MIME 类型
    file_size INTEGER,                       -- 文件大小（字节）
    duration INTEGER,                        -- 视频时长（秒，可选）
    thumbnail_path TEXT,                     -- 封面图路径（可选）
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (uploader_id) REFERENCES users (id)
);

CREATE INDEX idx_videos_uploader_id ON videos (uploader_id);
CREATE INDEX idx_videos_id ON videos (id);
```

### 1.2 修改推文表

```sql
ALTER TABLE tweets ADD COLUMN video_ids TEXT;
-- 存储格式：JSON 数组 ["1","2","3"]
```

### 1.3 修改消息表

```sql
ALTER TABLE messages ADD COLUMN type TEXT DEFAULT 'text';
-- 类型：'text' | 'image' | 'video'
```

---

## 二、后端 API 设计

### 2.1 视频上传接口

```python
POST /api/v2/video/upload
Content-Type: multipart/form-data

Request:
- file: UploadFile (video/mp4, video/webm, video/quicktime)
- 最大大小：100MB

Response:
{
    "id": 1,
    "filename": "myvideo.mp4",
    "file_type": "video/mp4",
    "file_size": 52428800,
    "url": "/api/v2/video/file/1"
}
```

**实现文件：** `app/api/v2/endpoints/video.py`

### 2.2 视频文件访问接口

```python
GET /api/v2/video/file/{video_id}
Response: Video file (streaming)
Content-Type: video/mp4
```

**实现文件：** `app/api/v2/endpoints/video.py`

### 2.3 视频信息接口

```python
GET /api/v2/video/{video_id}
Response:
{
    "id": 1,
    "filename": "myvideo.mp4",
    "file_type": "video/mp4",
    "file_size": 52428800,
    "duration": null,
    "created_at": "2026-03-13T22:00:00",
    "url": "/api/v2/video/file/1"
}
```

### 2.4 视频删除接口

```python
DELETE /api/v2/video/{video_id}
Response: {"msg": "删除成功"}
```

---

## 三、文件存储设计

### 3.1 存储目录结构

```
/home/admin/python_project/
└── static/
    └── videos/
        ├── {uuid}_{filename}.mp4    # 视频文件
        └── thumbnails/               # 封面图（可选）
            └── {uuid}_thumb.jpg
```

### 3.2 文件命名规则

```python
import uuid
unique_filename = f"{uuid.uuid4()}_{original_filename}"
# 示例：550e8400-e29b-41d4-a716-446655440000_myvideo.mp4
```

### 3.3 路径存储

数据库存储相对路径：
```
file_path: "/static/videos/550e8400-e29b-41d4-a716-446655440000_myvideo.mp4"
```

---

## 四、前端修改

### 4.1 聊天页面

#### 4.1.1 添加视频上传按钮

**文件：** `frontend/static/js/templates/chat.template.js`

```html
<!-- 在输入栏添加视频按钮 -->
<label class="input-action-btn" title="上传视频">
    <svg viewBox="0 0 24 24" width="24" height="24" fill="none" 
         stroke="currentColor" stroke-width="2">
        <polygon points="23 7 16 12 23 17 23 7"></polygon>
        <rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect>
    </svg>
    <input type="file" accept="video/*" class="hidden" @change="sendVideo">
</label>
```

#### 4.1.2 视频消息渲染

```html
<div class="bubble bubble-other">
    <!-- 文本 -->
    <span x-show="msg.type === 'text'" x-html="renderMarkdown(msg.content)"></span>
    
    <!-- 图片 -->
    <img x-if="msg.type === 'image'" :src="getImageUrl(msg.content)" ...>
    
    <!-- 视频（新增） -->
    <video x-if="msg.type === 'video'" 
           :src="getVideoUrl(msg.content)" 
           controls 
           style="max-width: 300px; border-radius: 8px;">
    </video>
</div>
```

#### 4.1.3 JavaScript 方法

**文件：** `frontend/static/js/module.chat.js`

```javascript
// 发送视频
async sendVideo(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    // 验证大小（100MB）
    if (file.size > 100 * 1024 * 1024) {
        this.showToast('视频大小不能超过 100MB', 'error');
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        const res = await this.api('/v2/video/upload', 'POST', formData, true);
        
        // 发送视频消息
        window.WS.send({
            event: "send_message",
            data: {
                conversation_id: this.currentChat.id,
                content: res.id.toString(),
                type: 'video'
            }
        });
        
        this.showToast('视频已发送', 'success');
    } catch (error) {
        this.showToast('视频上传失败：' + error.message, 'error');
    }
}

// 获取视频 URL
window.getVideoUrl = function(videoId) {
    if (!videoId) return '';
    return `/api/v2/video/file/${videoId}`;
};
```

### 4.2 推文发布页面

#### 4.2.1 添加视频选择

**文件：** `frontend/index.html`

```html
<!-- 在发布工具栏添加视频按钮 -->
<label class="compose-tool-btn" title="添加视频">
    🎬
    <input type="file" accept="video/*" @change="handleVideoSelect">
</label>
```

#### 4.2.2 视频预览

```html
<div x-show="composeVideos.length > 0" class="video-preview">
    <template x-for="(video, index) in composeVideos" :key="index">
        <div class="video-item">
            <video :src="video.preview" controls style="max-width: 200px;"></video>
            <button @click="removeVideo(index)">✕</button>
        </div>
    </template>
</div>
```

#### 4.2.3 JavaScript 方法

**文件：** `frontend/static/js/module.tweet.js`

```javascript
// 状态
composeVideos: [],  // 视频列表（限制 1 个）

// 选择视频
async handleVideoSelect(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    if (file.size > 100 * 1024 * 1024) {
        this.showToast('视频大小不能超过 100MB', 'error');
        return;
    }
    
    // 限制 1 个视频
    if (this.composeVideos.length >= 1) {
        this.showToast('最多只能上传 1 个视频', 'error');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    const res = await this.api('/v2/video/upload', 'POST', formData, true);
    
    this.composeVideos.push({
        id: res.id,
        preview: URL.createObjectURL(file)
    });
}

// 发布推文
async publishTweet() {
    await this.api('/v2/tweet/create', 'POST', {
        tweet: this.composeContent,
        tags: this.composeTags.join(','),
        is_published: true,
        image_ids: this.composeImageIds,
        video_ids: this.composeVideos.map(v => v.id)
    });
}
```

### 4.3 推文展示页面

#### 4.3.1 列表页视频展示

**文件：** `frontend/index.html`

```html
<div class="tweet-card">
    <!-- 图片 -->
    <div x-show="tweet.image_ids && tweet.image_ids.length > 0" class="tweet-images">...</div>
    
    <!-- 视频（新增） -->
    <div x-show="tweet.video_ids && tweet.video_ids.length > 0" class="tweet-video">
        <video :src="getVideoUrl(tweet.video_ids[0])" controls 
               style="max-width: 100%; border-radius: 8px;">
        </video>
    </div>
</div>
```

#### 4.3.2 详情页视频展示

```html
<div class="tweet-detail-content">
    <!-- 文本 -->
    <div x-html="renderMarkdown(currentTweet.tweet)"></div>
    
    <!-- 图片 -->
    <div x-show="currentTweet.image_ids" class="tweet-images">...</div>
    
    <!-- 视频（新增） -->
    <div x-show="currentTweet.video_ids && currentTweet.video_ids.length > 0" class="tweet-video">
        <video :src="getVideoUrl(currentTweet.video_ids[0])" controls 
               style="max-width: 100%; border-radius: 8px; margin-top: 15px;">
        </video>
    </div>
</div>
```

---

## 五、后端实现文件

### 5.1 新增文件

```
app/
├── api/v2/endpoints/
│   └── video.py              # 视频 API（新增）
├── services/
│   └── video_service.py      # 视频服务（新增）
└── database/models/
    └── video.py              # 视频模型（新增）
```

### 5.2 修改文件

```
app/
├── api/v2/router.py          # 添加 video router
├── services/
│   └── tweet_service.py      # 添加 video_ids 支持
└── database/schemas/
    └── tweet.py              # 添加 video_ids 字段
```

---

## 六、代码量估算

| 模块 | 文件 | 新增行数 |
|------|------|---------|
| **后端** | | |
| 视频 API | `video.py` | +150 |
| 视频服务 | `video_service.py` | +100 |
| 视频模型 | `video.py` | +30 |
| Router | `router.py` | +5 |
| 推文服务 | `tweet_service.py` | +30 |
| **前端** | | |
| 聊天模块 | `module.chat.js` | +100 |
| 聊天模板 | `chat.template.js` | +30 |
| 推文模块 | `module.tweet.js` | +100 |
| 推文模板 | `index.html` | +50 |
| **数据库** | | |
| SQL 脚本 | `migrations/` | +50 |
| **总计** | | **~745 行** |

---

## 七、实施步骤

### 阶段 1：后端基础（2 小时）
1. ✅ 创建 `videos` 表
2. ✅ 创建 `video.py` 模型
3. ✅ 创建 `video_service.py`
4. ✅ 创建 `video.py` API
5. ✅ 测试上传/下载

### 阶段 2：聊天视频（2 小时）
1. ✅ 前端添加视频上传按钮
2. ✅ 实现 `sendVideo()` 方法
3. ✅ 消息渲染支持 `<video>`
4. ✅ 测试聊天发送视频

### 阶段 3：推文视频（2 小时）
1. ✅ `tweets` 表添加 `video_ids`
2. ✅ 前端添加视频选择
3. ✅ 推文发布支持视频
4. ✅ 推文列表/详情展示
5. ✅ 测试

### 阶段 4：优化（可选）
- 视频封面生成
- 视频时长提取
- 进度条拖拽优化
- 移动端适配

**总计：6 小时**

---

## 八、测试用例

### 8.1 后端测试
- [ ] 上传 MP4 视频（< 100MB）
- [ ] 上传 WebM 视频
- [ ] 上传 MOV 视频
- [ ] 拒绝超过 100MB 文件
- [ ] 拒绝非视频文件
- [ ] 视频文件下载
- [ ] 视频信息获取
- [ ] 视频删除（包括文件）

### 8.2 聊天测试
- [ ] 选择视频文件
- [ ] 发送视频消息
- [ ] 接收视频消息
- [ ] 视频播放控制
- [ ] 多视频消息

### 8.3 推文测试
- [ ] 发布带视频的推文
- [ ] 视频 + 文本混合
- [ ] 视频 + 图片混合
- [ ] 列表页视频展示
- [ ] 详情页视频播放

---

## 九、风险与应对

| 风险 | 影响 | 应对措施 |
|------|------|---------|
| 大文件上传超时 | 上传失败 | 增加超时时间到 300 秒 |
| 磁盘空间不足 | 无法上传 | 定期检查，清理无用视频 |
| 视频格式兼容性 | 部分浏览器不播放 | 限制 MP4/WebM 格式 |
| 并发上传冲突 | 文件覆盖 | 使用 UUID 命名 |
| 安全性 | 恶意文件上传 | 验证 MIME type + 文件头 |

---

## 十、目录结构

```
/home/admin/python_project/
├── app/
│   ├── api/v2/endpoints/
│   │   ├── video.py              ⭐ 新增
│   │   └── image.py
│   ├── services/
│   │   ├── video_service.py      ⭐ 新增
│   │   └── image_service.py
│   └── database/models/
│       ├── video.py              ⭐ 新增
│       └── image.py
├── static/
│   └── videos/                   ⭐ 新增目录
│       ├── {uuid}_{filename}.mp4
│       └── thumbnails/
├── frontend/
│   └── static/js/
│       ├── module.chat.js        ✏️ 修改
│       └── module.tweet.js       ✏️ 修改
└── migrations/
    └── add_video_support.sql     ⭐ 新增
```

---

## 十一、总结

**方案优势：**
1. ✅ 视频存本地，不占用数据库空间
2. ✅ 支持大文件（100MB+）
3. ✅ 直接文件访问，性能好
4. ✅ 易于备份和迁移
5. ✅ 支持流式播放

**实施时间：** 6 小时  
**代码量：** ~745 行  
**风险等级：** 低

**推荐立即实施！** 🚀
