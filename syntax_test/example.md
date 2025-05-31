# QuickServer 语法高亮测试

> 这是一个用于测试 **Markdown 语法高亮** 功能的文档文件  
> 包含了各种 Markdown 语法特性和代码块示例

## 目录

- [基本语法](#基本语法)
- [代码块示例](#代码块示例)
- [表格和列表](#表格和列表)
- [链接和图片](#链接和图片)
- [高级功能](#高级功能)

---

## 基本语法

### 标题样式

# 一级标题 (H1)
## 二级标题 (H2)  
### 三级标题 (H3)
#### 四级标题 (H4)
##### 五级标题 (H5)
###### 六级标题 (H6)

### 文本格式

这是 **粗体文本** 和 __另一种粗体__  
这是 *斜体文本* 和 _另一种斜体_  
这是 ***粗斜体文本*** 和 ___另一种粗斜体___  
这是 ~~删除线文本~~  
这是 `行内代码` 文本  
这是 ==高亮文本== (扩展语法)

### 引用

> 这是一个简单的引用
> 
> > 这是嵌套引用
> > 
> > **作者**: xyanmi  
> > **项目**: QuickServer

### 分隔线

---
***
___

## 代码块示例

### Python 代码

```python
#!/usr/bin/env python3
"""
QuickServer 示例代码
演示 Python 语法高亮
"""

import os
import asyncio
from typing import List, Dict, Optional

class QuickServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8000):
        self.host = host
        self.port = port
        self.routes: Dict[str, callable] = {}
    
    async def start(self) -> None:
        """启动服务器"""
        print(f"🚀 Starting server at http://{self.host}:{self.port}")
        
        try:
            # 服务器启动逻辑
            await self._run_server()
        except KeyboardInterrupt:
            print("👋 Server stopped by user")
        except Exception as e:
            print(f"❌ Server error: {e}")
    
    def route(self, path: str):
        """路由装饰器"""
        def decorator(func):
            self.routes[path] = func
            return func
        return decorator

# 使用示例
server = QuickServer()

@server.route("/api/status")
async def status_handler():
    return {"status": "ok", "message": "服务器运行正常"}

if __name__ == "__main__":
    asyncio.run(server.start())
```

### JavaScript 代码

```javascript
/**
 * QuickServer 前端代码示例
 * 演示现代 JavaScript 语法高亮
 */

// ES6+ 特性示例
class FileManager {
    #apiBase = '/api';  // 私有字段
    
    constructor(config = {}) {
        this.config = {
            timeout: 5000,
            retries: 3,
            ...config
        };
        this.cache = new Map();
    }
    
    // 异步文件操作
    async uploadFile(file, options = {}) {
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const response = await fetch(`${this.#apiBase}/upload`, {
                method: 'POST',
                body: formData,
                signal: AbortSignal.timeout(this.config.timeout),
                ...options
            });
            
            if (!response.ok) {
                throw new Error(`Upload failed: ${response.status}`);
            }
            
            const result = await response.json();
            this.cache.set(file.name, result);
            
            return result;
        } catch (error) {
            console.error('Upload error:', error);
            throw error;
        }
    }
    
    // 解构赋值和模板字符串
    displayFileInfo({ name, size, type, lastModified }) {
        const sizeFormatted = this.formatFileSize(size);
        const dateFormatted = new Date(lastModified).toLocaleString();
        
        return `
            📄 文件名: ${name}
            📏 大小: ${sizeFormatted}
            🏷️ 类型: ${type}
            📅 修改时间: ${dateFormatted}
        `;
    }
    
    // 箭头函数和数组方法
    formatFileSize = (bytes) => {
        const units = ['B', 'KB', 'MB', 'GB'];
        const index = Math.floor(Math.log(bytes) / Math.log(1024));
        return `${(bytes / Math.pow(1024, index)).toFixed(2)} ${units[index]}`;
    };
}

// 使用示例
const fileManager = new FileManager({ timeout: 10000 });
document.getElementById('fileInput').addEventListener('change', async (e) => {
    const files = Array.from(e.target.files);
    
    for (const file of files) {
        try {
            await fileManager.uploadFile(file);
            console.log('✅', fileManager.displayFileInfo(file));
        } catch (error) {
            console.error('❌', error.message);
        }
    }
});
```

### HTML/CSS 代码

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QuickServer - 语法高亮测试</title>
    <style>
        :root {
            --primary-color: #3498db;
            --secondary-color: #2ecc71;
            --danger-color: #e74c3c;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .highlight-box {
            background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
            border-radius: 8px;
            padding: 20px;
            color: white;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="highlight-box">
            <h1>🎨 CSS 语法高亮测试</h1>
            <p>展示 HTML 和 CSS 的语法高亮效果</p>
        </div>
    </div>
</body>
</html>
```

### SQL 代码

```sql
-- QuickServer 数据库示例
-- 演示 SQL 语法高亮

-- 创建用户表
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

-- 创建文件表
CREATE TABLE files (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    original_name VARCHAR(255) NOT NULL,
    file_size BIGINT NOT NULL,
    mime_type VARCHAR(100),
    upload_path TEXT NOT NULL,
    uploaded_by INTEGER REFERENCES users(id),
    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    download_count INTEGER DEFAULT 0,
    is_public BOOLEAN DEFAULT false
);

-- 创建索引
CREATE INDEX idx_files_uploaded_by ON files(uploaded_by);
CREATE INDEX idx_files_upload_time ON files(upload_time);
CREATE INDEX idx_users_username ON users(username);

-- 查询示例
WITH file_stats AS (
    SELECT 
        u.username,
        COUNT(f.id) as file_count,
        SUM(f.file_size) as total_size,
        AVG(f.download_count) as avg_downloads
    FROM users u
    LEFT JOIN files f ON u.id = f.uploaded_by
    WHERE u.is_active = true
    GROUP BY u.id, u.username
)
SELECT 
    username,
    file_count,
    pg_size_pretty(total_size) as formatted_size,
    ROUND(avg_downloads::numeric, 2) as avg_downloads
FROM file_stats
WHERE file_count > 0
ORDER BY total_size DESC
LIMIT 10;

-- 存储过程示例
CREATE OR REPLACE FUNCTION update_download_count(file_id INTEGER)
RETURNS void AS $$
BEGIN
    UPDATE files 
    SET download_count = download_count + 1,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = file_id;
    
    -- 记录下载日志
    INSERT INTO download_logs (file_id, download_time, ip_address)
    VALUES (file_id, CURRENT_TIMESTAMP, inet_client_addr());
END;
$$ LANGUAGE plpgsql;
```

## 表格和列表

### 无序列表

- 🚀 QuickServer 主要功能
  - 文件浏览和导航
  - 文件上传下载
  - 代码语法高亮
  - 响应式设计
- 📦 支持的文件类型
  - 文本文件 (`.txt`, `.md`, `.py`, `.js` 等)
  - 图片文件 (`.jpg`, `.png`, `.gif` 等)
  - 文档文件 (`.pdf`)
- 🎨 界面特性
  - 现代化设计
  - 移动端适配
  - 暗色主题

### 有序列表

1. **项目初始化**
   1. 创建项目目录
   2. 初始化 Git 仓库
   3. 设置基本配置

2. **核心开发**
   1. 实现服务器逻辑
   2. 设计用户界面
   3. 添加文件操作功能

3. **测试和优化**
   1. 单元测试
   2. 集成测试
   3. 性能优化

### 任务列表

- [x] ✅ 基础服务器功能
- [x] ✅ 文件上传下载
- [x] ✅ 语法高亮
- [ ] 🔄 用户认证系统
- [ ] 📋 文件分享功能
- [ ] 🌙 暗色主题

### 表格示例

| 功能 | 状态 | 版本 | 描述 |
|------|------|------|------|
| 文件浏览 | ✅ 完成 | v0.1.0 | 基础的文件和目录浏览功能 |
| 文件上传 | ✅ 完成 | v0.1.0 | 支持多文件上传和拖拽上传 |
| 语法高亮 | ✅ 完成 | v0.1.0 | 20+ 种编程语言的语法高亮 |
| 文件下载 | ✅ 完成 | v0.1.0 | 支持单文件和文件夹打包下载 |
| 用户认证 | 🔄 开发中 | v0.2.0 | 基于 JWT 的用户认证系统 |
| 暗色主题 | 📋 计划中 | v0.2.0 | 支持明暗主题切换 |

## 链接和图片

### 链接示例

- [QuickServer GitHub 仓库](https://github.com/xyanmi/quickserver)
- [Python 官方文档](https://docs.python.org/3/)
- [Markdown 语法指南](https://www.markdownguide.org/)
- [开发者博客](https://blog.example.com) "可选的标题"

### 图片示例

![QuickServer Logo](https://via.placeholder.com/400x200/3498db/ffffff?text=QuickServer "QuickServer 标志")

*图: QuickServer 项目标志*

### 参考链接

[quickserver]: https://github.com/xyanmi/quickserver "QuickServer 项目"
[python]: https://python.org "Python 编程语言"
[markdown]: https://daringfireball.net/projects/markdown/ "Markdown 语法"

访问 [QuickServer][quickserver] 项目，了解更多关于 [Python][python] 和 [Markdown][markdown] 的信息。

## 高级功能

### 脚注

这是一个带脚注的文本[^1]，还有另一个脚注[^note]。

[^1]: 这是第一个脚注的内容
[^note]: 这是一个命名脚注的内容，支持多行文本
    
    甚至可以包含代码：`console.log('Hello World')`

### 定义列表

术语 1
: 这是术语 1 的定义

术语 2
: 这是术语 2 的定义
: 术语可以有多个定义

### 数学公式 (如果支持)

行内公式：$E = mc^2$

块级公式：
$$
\int_{-\infty}^{\infty} e^{-x^2} dx = \sqrt{\pi}
$$

### 代码高亮 (指定语言)

```bash
# 启动 QuickServer
python -m quickserver --port 8080 --host 0.0.0.0

# 安装依赖
pip install quickserver

# 查看帮助
quickserver --help
```

### 警告框 (扩展语法)

> **⚠️ 注意**  
> 这是一个警告信息，请注意安全配置。

> **💡 提示**  
> 使用 `--debug` 参数可以启用调试模式。

> **❌ 错误**  
> 文件上传失败，请检查文件大小限制。

---

## 结语

这个文档展示了 Markdown 的各种语法特性，包括：

- ✅ 基本文本格式
- ✅ 标题和列表
- ✅ 代码块和语法高亮
- ✅ 表格和链接
- ✅ 图片和引用
- ✅ 高级功能

**感谢使用 QuickServer！** 🎉

---

*最后更新: 2024年3月15日*  
*文档版本: v1.0* 