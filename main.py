from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.message_components import Plain, Image
import re
import aiohttp
import os
import asyncio
from typing import List, Optional, Dict
from urllib.parse import urlparse

@register("qq_official_url_cleaner", "ave_mujica-saki", "为QQ官方API修改发送消息的链接，将URL图片转换为直接发送的图片", "1.0.0", "https://github.com/AstrBot-Devs/qq_official_url_cleaner")
class QQOfficialUrlCleaner(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.svg', '.ico'}
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.temp_dir = "temp_images"
        
        # 配置选项
        self.block_non_image_urls = True  # 是否屏蔽非图片URL
        self.show_url_blocked_message = True  # 是否显示链接被屏蔽的提示
        self.url_replacement_text = "[链接已屏蔽]"  # 替换被屏蔽URL的文本
        
        # 预设的表情图片URL配置
        self.emoji_urls = {
            # 可以在这里添加固定的表情图片URL
            # "happy": "https://example.com/happy.gif",
            # "sad": "https://example.com/sad.png",
        }
        
    async def initialize(self):
        """初始化插件，创建临时目录"""
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
            logger.info(f"创建临时图片目录: {self.temp_dir}")

    def is_image_url(self, url: str) -> bool:
        """检查URL是否为图片URL"""
        try:
            parsed = urlparse(url)
            path = parsed.path.lower()
            return any(path.endswith(ext) for ext in self.image_extensions)
        except:
            return False

    async def download_image(self, url: str) -> Optional[str]:
        """下载图片到临时目录"""
        try:
            # 验证URL格式
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                logger.warning(f"无效的URL格式: {url}")
                return None
                
            # 获取文件扩展名
            path = parsed.path.lower()
            ext = os.path.splitext(path)[1]
            
            if ext not in self.image_extensions:
                logger.info(f"非支持的图片格式: {url}, 扩展名: {ext}")
                return None
                
            # 生成临时文件名
            import uuid
            filename = f"{uuid.uuid4()}{ext}"
            filepath = os.path.join(self.temp_dir, filename)
            
            logger.info(f"开始下载图片: {url}")
            
            # 下载图片
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        content_length = response.headers.get('Content-Length')
                        if content_length and int(content_length) > self.max_file_size:
                            logger.warning(f"图片文件过大: {url}, 大小: {content_length} bytes")
                            return None
                            
                        # 验证内容类型
                        content_type = response.headers.get('Content-Type', '')
                        if not any(img_type in content_type.lower() for img_type in ['image/', 'application/octet-stream']):
                            logger.warning(f"非图片内容类型: {url}, Content-Type: {content_type}")
                            return None
                            
                        with open(filepath, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)
                        
                        # 验证文件是否成功写入
                        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                            logger.info(f"成功下载图片: {url} -> {filepath} ({os.path.getsize(filepath)} bytes)")
                            return filepath
                        else:
                            logger.error(f"图片文件写入失败或为空: {url}")
                            
                    else:
                        logger.error(f"下载图片失败: {url}, 状态码: {response.status}")
                        
        except asyncio.TimeoutError:
            logger.error(f"下载图片超时: {url}")
        except Exception as e:
            logger.error(f"下载图片出错: {url}, 错误: {type(e).__name__}: {str(e)}")
            
        return None

    async def cleanup_temp_file(self, filepath: str):
        """清理临时文件"""
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"删除临时文件: {filepath}")
        except Exception as e:
            logger.error(f"删除临时文件失败: {filepath}, 错误: {str(e)}")

    @filter.on_decorating_result()
    async def handle_bot_response(self, event: AstrMessageEvent):
        """处理机器人回复中的URL，将图片URL转换为直接发送的图片"""
        result = event.get_result()
        if not result or not result.chain:
            return
            
        new_chain = []
        downloaded_images = []  # 记录下载的图片路径
        
        for message in result.chain:
            if isinstance(message, Plain):
                text = message.text
                
                # 查找所有URL - 修复正则表达式，移除不支持的\p{P}
                url_pattern = r'https?://[^\s\u4e00-\u9fa5()，。！？；：""''（）【】《》〈〉「」『』〔〕［］｛｝]+'
                urls = re.findall(url_pattern, text)
                
                if not urls:
                    new_chain.append(message)
                    continue
                
                # 处理每个URL
                last_pos = 0
                for url in urls:
                    url_start = text.find(url, last_pos)
                    
                    # 添加URL前的文本
                    if url_start > last_pos:
                        prefix_text = text[last_pos:url_start]
                        if prefix_text.strip():
                            new_chain.append(Plain(prefix_text))
                    
                    # 检查是否为图片URL
                    if self.is_image_url(url):
                        # 下载图片
                        filepath = await self.download_image(url)
                        if filepath:
                            # 添加图片到消息链
                            new_chain.append(Image(file=filepath))
                            downloaded_images.append(filepath)
                            logger.info(f"将URL转换为图片: {url}")
                        else:
                            # 下载失败，保留原始URL但添加提示
                            new_chain.append(Plain(f"[图片下载失败: {url}]"))
                    else:
                        # 处理非图片URL
                        if self.block_non_image_urls:
                            logger.info(f"屏蔽非图片URL: {url}")
                            if self.show_url_blocked_message:
                                new_chain.append(Plain(self.url_replacement_text))
                            # 如果不显示消息，则完全移除URL
                        else:
                            # 不屏蔽URL，但QQ官方API可能会拒绝发送
                            logger.warning(f"尝试发送非图片URL，可能被QQ官方API拒绝: {url}")
                            new_chain.append(Plain(url))
                    
                    last_pos = url_start + len(url)
                
                # 添加剩余文本
                if last_pos < len(text):
                    remaining_text = text[last_pos:]
                    if remaining_text.strip():
                        new_chain.append(Plain(remaining_text))
                        
            else:
                # 非文本消息，直接添加
                new_chain.append(message)
        
        # 更新消息链
        result.chain = new_chain
        
        # 延迟清理临时文件
        if downloaded_images:
            for filepath in downloaded_images:
                asyncio.create_task(self.delayed_cleanup(filepath))

    async def delayed_cleanup(self, filepath: str, delay: int = 60):
        """延迟清理临时文件"""
        await asyncio.sleep(delay)
        await self.cleanup_temp_file(filepath)

    async def terminate(self):
        """插件卸载时清理临时目录"""
        try:
            if os.path.exists(self.temp_dir):
                for filename in os.listdir(self.temp_dir):
                    filepath = os.path.join(self.temp_dir, filename)
                    if os.path.isfile(filepath):
                        os.remove(filepath)
                os.rmdir(self.temp_dir)
                logger.info(f"清理临时图片目录: {self.temp_dir}")
        except Exception as e:
            logger.error(f"清理临时目录失败: {str(e)}")