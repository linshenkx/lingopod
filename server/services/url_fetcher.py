import os
import json
import requests
from bs4 import BeautifulSoup
from typing import Tuple, Optional
from urllib.parse import urlparse
from core.logging import log
from utils.decorators import error_handler

class URLContentError(Exception):
    """URL内容获取错误"""
    pass

@error_handler
def fetch_url_content(url: str) -> Tuple[str, Optional[str]]:
    """
    获取URL内容，返回 (正文内容, 标题)
    
    Args:
        url: 要获取的网页URL
        task_id: 任务ID，用于日志记录
        
    Returns:
        Tuple[str, Optional[str]]: (正文内容, 标题)
        
    Raises:
        URLContentError: 当内容获取失败时抛出
    """
    log.info(f"开始获取URL内容: {url}")
    
    try:
        # 设置请求头
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # 发送请求
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()  # 检查响应状态
        
        # 设置正确的编码
        response.encoding = response.apparent_encoding
        
        # 使用BeautifulSoup解析内容
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 移除不需要的标签
        for tag in soup(['script', 'style', 'nav', 'footer', 'iframe']):
            tag.decompose()
        
        # 获取标题
        title = None
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text().strip()
        
        # 获取正文内容
        # 首先尝试获取文章主体
        article = soup.find('article')
        if not article:
            article = soup.find('main')
        if not article:
            article = soup.find('div', class_=['content', 'article', 'post'])
        
        if article:
            content = article.get_text(separator='\n', strip=True)
        else:
            # 如果找不到明确的文章区域，获取所有段落文本
            paragraphs = soup.find_all('p')
            content = '\n'.join(p.get_text().strip() for p in paragraphs if p.get_text().strip())
        
        # 清理和格式化内容
        content = clean_content(content)
        
        if not content:
            raise URLContentError("无法提取有效内容")
        
        log.info(f"成功获取URL内容，长度: {len(content)}字")
        return content, title
        
    except requests.RequestException as e:
        error_msg = f"请求URL失败: {str(e)}"
        log.error(error_msg)
        raise URLContentError(error_msg)
    
    except Exception as e:
        error_msg = f"获取URL内容时发生错误: {str(e)}"
        log.error(error_msg)
        raise URLContentError(error_msg)

def clean_content(content: str) -> str:
    """
    清理和格式化内容
    
    Args:
        content: 原始内容文本
        
    Returns:
        str: 清理后的内容
    """
    # 分行处理
    lines = content.split('\n')
    
    # 清理每一行
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        # 跳过空行和太短的行
        if line and len(line) > 2:
            cleaned_lines.append(line)
    
    # 合并行
    cleaned_content = '\n'.join(cleaned_lines)
    
    # 删除多余的空白字符
    cleaned_content = ' '.join(cleaned_content.split())
    
    return cleaned_content

def save_content(content: str, title: Optional[str], task_id: str, task_dir: str):
    """
    保存获取的内容到文件
    
    Args:
        content: 网页内容
        title: 网页标题
        task_id: 任务ID
        task_dir: 任务目录
    """
    content_file = os.path.join(task_dir, 'content.json')
    content_data = {
        'content': content,
        'title': title
    }
    
    with open(content_file, 'w', encoding='utf-8') as f:
        json.dump(content_data, f, ensure_ascii=False, indent=2)
    
    log.info(f"已保存内容到文件: {content_file}")
