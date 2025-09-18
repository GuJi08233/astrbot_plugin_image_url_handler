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
            # 获取文件扩展名
            parsed = urlparse(url)
            path = parsed.path.lower()
            ext = os.path.splitext(path)[1]
            
            if ext not in self.image_extensions:
                return None
                
            # 生成临时文件名
            import uuid
            filename = f"{uuid.uuid4()}{ext}"
            filepath = os.path.join(self.temp_dir, filename)
            
            # 下载图片
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as response:
                    if response.status == 200:
                        content_length = response.headers.get('Content-Length')
                        if content_length and int(content_length) > self.max_file_size:
                            logger.warning(f"图片文件过大: {url}")
                            return None
                            
                        with open(filepath, 'wb') as f:
                            async for chunk in response.content.iter_chunked(8192):
                                f.write(chunk)
                        
                        logger.info(f"成功下载图片: {url} -> {filepath}")
                        return filepath
                    else:
                        logger.error(f"下载图片失败: {url}, 状态码: {response.status}")
                        
        except Exception as e:
            logger.error(f"下载图片出错: {url}, 错误: {str(e)}")
            
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
                
                # 查找所有URL
                url_pattern = r'https?://[^\s\u4e00-\u9fa5\p{P}()]+'
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
                        # 非图片URL，可以选择屏蔽或保留
                        # new_chain.append(Plain("[被屏蔽的链接]"))
                        new_chain.append(Plain(url))  # 保留非图片URL
                    
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