# QQ Official URL Cleaner - AstrBot插件

## 功能介绍

这个插件专门为QQ官方API设计，可以自动检测机器人回复消息中的图片URL，并将其转换为直接发送的图片，避免消息被屏蔽。

## 解决的问题

QQ官方机器人不允许直接发送URL，但机器人的回复中可能包含图片链接（如表情图片、固定回复图片等）。这个插件可以：

1. **拦截机器人回复**：使用 `@filter.on_decorating_result()` 拦截机器人的回复消息
2. **检测图片URL**：识别回复中的图片链接（PNG、JPG、GIF、WebP、SVG、ICO等格式）
3. **自动下载转换**：将图片URL下载并转换为可直接发送的图片消息组件
4. **保持文本结构**：保留原始文本结构，只替换图片URL部分

## 支持的图片格式

- PNG (`.png`)
- JPEG (`.jpg`, `.jpeg`)
- GIF (`.gif`)
- WebP (`.webp`)
- BMP (`.bmp`)
- SVG (`.svg`)
- ICO (`.ico`)

## 支持的特殊链接

### 表情包API链接
支持处理会重定向到真实图片的表情包API链接，例如：
- `https://krcpsqplffnigtjeshns.supabase.co/functions/v1/random/biaoqing?folderkey=smile&seed=12345`
- `https://pub-2efc7fc7514c4166a7f59dadc036954f.r2.dev/meng/meng.webp`

这些链接会重定向到真实的图片文件，插件会自动处理重定向并下载最终图片。

## 工作原理

1. **消息拦截**：使用 `@filter.on_decorating_result()` 装饰器拦截机器人的所有回复
2. **URL检测**：使用正则表达式检测URL（修复了`\p{P}`错误）
3. **图片识别**：检查URL路径是否以图片扩展名结尾，或识别表情包API链接
4. **异步下载**：使用 `aiohttp` 异步下载图片到临时目录，支持处理重定向
5. **消息链重构**：将原始文本分割，图片部分替换为 `Image` 组件
6. **自动清理**：延迟60秒后清理临时文件

## 使用示例

### 示例1：普通图片链接
#### 原始机器人回复：
```
你好！这是一个表情 [https://example.com/happy.gif] 祝你开心！
```

#### 插件处理后的实际发送：
```
你好！这是一个表情 [图片] 祝你开心！
```

实际会发送：
- 文本："你好！这是一个表情 "
- 图片：下载的 happy.gif
- 文本：" 祝你开心！"

### 示例2：表情包API链接
#### 原始机器人回复：
```
送你一个微笑 [https://krcpsqplffnigtjeshns.supabase.co/functions/v1/random/biaoqing?folderkey=smile&seed=12345] 希望你开心！
```

#### 插件处理后的实际发送：
```
送你一个微笑 [图片] 希望你开心！
```

插件会自动处理重定向，下载真实的图片文件。

## 配置选项

在代码中可以修改以下配置：

```python
# 支持的图片格式
self.image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.svg', '.ico'}

# 最大文件大小限制（默认10MB）
self.max_file_size = 10 * 1024 * 1024

# 临时文件目录
self.temp_dir = "temp_images"

# URL处理配置
self.block_non_image_urls = True  # 是否屏蔽非图片URL
self.show_url_blocked_message = True  # 是否显示链接被屏蔽的提示
self.url_replacement_text = "[链接已屏蔽]"  # 替换被屏蔽URL的文本

# 预设的表情图片URL（可选）
self.emoji_urls = {
    "happy": "https://example.com/happy.gif",
    "sad": "https://example.com/sad.png",
}
```

## 错误处理

插件包含完善的错误处理：

- **下载失败**：如果图片下载失败，会保留原始URL但添加"[图片下载失败]"提示
- **网络超时**：30秒超时保护
- **文件大小检查**：超过10MB的图片会被跳过
- **临时文件清理**：自动清理机制确保不留下垃圾文件

## 注意事项

1. **性能考虑**：大量图片同时下载可能影响响应速度
2. **存储空间**：临时文件会占用磁盘空间，建议定期清理
3. **网络依赖**：需要稳定的网络连接来下载图片
4. **版权问题**：确保机器人回复中的图片URL有合法使用权

## 与其他插件的区别

- **不是处理用户输入**：专门处理机器人**回复**中的URL
- **保持消息结构**：不会简单替换为"[被屏蔽的链接]"，而是智能转换
- **支持多种格式**：不仅限于常见图片格式，还包括SVG、ICO等

## 安装使用

1. 将插件文件夹放入AstrBot的插件目录
2. 重启AstrBot
3. 插件会自动工作，无需任何配置

## 更新日志

### v1.0.0
- 初始版本发布
- 支持机器人回复中的图片URL检测和转换
- 支持多种图片格式
- 智能消息链重构
- 自动临时文件清理

## 支持与反馈

如有问题或建议，请在项目仓库提交Issue。