# 视频功能设计方案

## 一、当前代码分析

### 1. 数据库结构
**推文表 (tweets):**
- `image_ids TEXT` - JSON 数组存储图片 ID `["1","2","3"]`
- 无视频字段

**图片表 (images):**
- `image_data TEXT` - Base64 编码
- `file_type VARCHAR(50)` - MIME 类型
- `file_size INTEGER` - 文件大小

### 2. 后端 API
**图片上传流程:**
```
POST /api/v2/image/upload
  ↓
ImageService.upload_image()
  ↓
Base64 编码 → 存入 images 表
  ↓
返回：{"id": 1, "url": "/api/v2/image/1"}
```

### 3. 前端结构
**聊天消息类型:**
- `msg.type === 'text'` - 文本
- `msg.type === 'image'` - 图片
- ❌ 缺少 `'video'` 类型

**推文发布:**
- 图片：`handleImageSelect()` + `composeImages[]`
- ❌ 缺少视频处理

---

## 二、设计方案（最小改动）

### 方案 A：复用图片表（推荐⭐）

**核心思路：** 视频和图片都存 `images` 表，用 `file_type` 区分

**优点：**
- ✅ 不修改数据库
- ✅ 复用现有 API
- ✅ 代码改动最小（< 200 行）

**缺点：**
- ⚠️ 视频 Base64 占用数据库空间

---

### 方案 B：新建视频表

**核心思路：** 独立 `videos` 表存储视频

**优点：**
- ✅ 数据结构清晰
- ✅ 易于扩展（时长、封面等）

**缺点：**
- ❌ 需要创建表
- ❌ 代码改动大（> 500 行）

---

## 三、推荐方案：方案 A 详细设计

### 1. 数据库（无需修改）

```sql
-- 复用 images 表
CREATE TABLE images (
    id INTEGER,
    image_data TEXT,      -- Base64（图片或视频）
    file_type VARCHAR(50), -- 'image/jpeg' 或 'video/mp4'
    file_size INTEGER,
    ...
);

-- 推文表添加 video_ids 字段
ALTER TABLE tweets ADD COLUMN video_ids TEXT;
```

### 2. 后端 API

#### 2.1 修改图片上传 API（支持视频）

**文件：** `app/api/v2/endpoints/image.py`

```python
@router.post("/upload", response_model=ImageOut)
async def upload_media(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_image_session)
):
    # 验证文件类型
    allowed_types = [
        'image/jpeg', 'image/png', 'image/gif',  # 图片
        'video/mp4', 'video/webm', 'video/quicktime'  # 视频
    ]
    
    if file.content_type not in allowed_types:
        raise HTTPException(400, "不支持的文件格式")
    
    # 验证大小
    if file.content_type.startswith('video/'):
        max_size = 100 * 1024 * 1024  # 100MB
    else:
        max_size = 5 * 1024 * 1024  # 5MB
    
    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(400, f"文件不能超过{max_size//1024//1024}MB")
    
    # 复用现有上传逻辑
    return await ImageService.upload_image(db, file, user_id)
```

#### 2.2 新增视频信息接口

```python
@router.get("/{media_id}/info")
async def get_media_info(media_id: int, db: AsyncSession):
    """获取媒体信息（判断是图片还是视频）"""
    media = await ImageService.get_image(db, media_id)
    return {
        "id": media.id,
        "file_type": media.file_type,
        "file_size": media.file_size,
        "is_video": media.file_type.startswith('video/')
    }
```

### 3. 前端实现

#### 3.1 聊天页面

**文件：** `frontend/static/js/templates/chat.template.js`

```html
<!-- 消息渲染 -->
<div class="bubble bubble-other">
    <!-- 文本 -->
    <span x-show="msg.type === 'text'" x-html="renderMarkdown(msg.content)"></span>
    
    <!-- 图片 -->
    <img x-if="msg.type === 'image'" :src="getImageUrl(msg.content)" ...>
    
    <!-- 视频（新增） -->
    <video x-if="msg.type === 'video'" 
           :src="getVideoUrl(msg.content)" 
           controls 
           style="max-width: 300px;">
    </video>
</div>
```

**文件：** `frontend/static/js/module.chat.js`

```javascript
// 发送视频
async sendVideo(event) {
    const file = event.target.files[0];
    if (!file || file.size > 100 * 1024 * 1024) {
        this.showToast('视频不能超过 100MB', 'error');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    const res = await this.api('/v2/image/upload', 'POST', formData, true);
    
    // 发送消息
    window.WS.send({
        event: "send_message",
        data: {
            conversation_id: this.currentChat.id,
            content: res.id.toString(),
            type: 'video'
        }
    });
}

// 获取视频 URL
window.getVideoUrl = function(mediaId) {
    return `/api/v2/image/${mediaId}`;
};
```

#### 3.2 推文发布

**文件：** `frontend/static/js/module.tweet.js`

```javascript
// 状态
composeVideos: [],  // 视频列表（限制 1 个）

// 选择视频
async handleVideoSelect(event) {
    const file = event.target.files[0];
    if (file.size > 100 * 1024 * 1024) {
        this.showToast('视频不能超过 100MB', 'error');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    const res = await this.api('/v2/image/upload', 'POST', formData, true);
    
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
        video_ids: this.composeVideos.map(v => v.id)  // 新增
    });
}
```

#### 3.3 推文展示

**文件：** `frontend/index.html`

```html
<!-- 推文列表 -->
<div class="tweet-card">
    <!-- 图片 -->
    <div x-show="tweet.image_ids.length > 0" class="tweet-images">...</div>
    
    <!-- 视频（新增） -->
    <div x-show="tweet.video_ids && tweet.video_ids.length > 0" class="tweet-video">
        <video :src="getVideoUrl(tweet.video_ids[0])" controls></video>
    </div>
</div>
```

---

## 四、实现步骤

### 阶段 1：聊天视频（2 小时）
1. ✅ 修改图片上传 API 支持视频
2. ✅ 前端添加视频上传按钮
3. ✅ 聊天消息渲染视频
4. ✅ 测试

### 阶段 2：推文视频（2 小时）
1. ✅ 推文表添加 `video_ids` 字段
2. ✅ 前端添加视频选择
3. ✅ 推文发布和展示
4. ✅ 测试

### 阶段 3：优化（可选）
- 视频封面生成
- 视频时长显示
- 进度条拖拽
- 自动播放控制

---

## 五、代码量估算

| 模块 | 文件 | 行数 |
|------|------|------|
| 后端 API | `image.py` | +50 |
| 聊天前端 | `module.chat.js` | +80 |
| 聊天模板 | `chat.template.js` | +20 |
| 推文前端 | `module.tweet.js` | +80 |
| 推文模板 | `index.html` | +30 |
| **总计** | | **~260 行** |

---

## 六、测试用例

### 聊天
- [ ] 上传 MP4 视频
- [ ] 上传 WebM 视频
- [ ] 超过 100MB 拒绝
- [ ] 视频正常播放
- [ ] 图片正常上传（回归测试）

### 推文
- [ ] 发布带视频的推文
- [ ] 视频 + 图片混合
- [ ] 视频列表展示
- [ ] 视频播放控制

---

## 七、风险与应对

| 风险 | 影响 | 应对 |
|------|------|------|
| Base64 占用空间 | 数据库膨胀 | 后续迁移到对象存储 |
| 视频格式兼容性 | 部分浏览器不播放 | 限制 MP4/WebM |
| 上传超时 | 大视频上传失败 | 增加超时时间 |

---

## 八、结论

**推荐方案 A（复用图片表）**

**理由：**
1. 最小改动（260 行代码）
2. 不修改数据库结构
3. 复用现有 API 和逻辑
4. 可快速上线验证

**实施时间：** 4 小时（含测试）
