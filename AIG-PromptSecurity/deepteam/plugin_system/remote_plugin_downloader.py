"""
远程插件下载器
支持从HTTP链接下载zip文件并解压到plugin目录
"""

import os
import re
import zipfile
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urlparse
import requests
from loguru import logger


class RemotePluginDownloader:
    """远程插件下载器"""
    
    def __init__(self, plugin_dir: Union[str, Path] = "./plugin"):
        self.plugin_dir = Path(plugin_dir)
        self.plugin_dir.mkdir(exist_ok=True)
        
    def is_remote_plugin_url(self, url: str) -> bool:
        """判断是否为远程插件URL"""
        if not url.startswith('http'):
            return False
        
        # 检查是否为zip文件链接或Python文件链接
        parsed_url = urlparse(url)
        path = parsed_url.path.lower()
        return path.endswith('.zip') or path.endswith('.py')
    
    def download_and_extract_plugin(self, url: str, force_download: bool = False) -> Dict[str, Any]:
        """下载并解压远程插件"""
        result = {
            'success': False,
            'downloaded_path': None,
            'extracted_path': None,
            'errors': [],
            'warnings': []
        }
        
        try:
            # 验证URL格式
            if not self.is_remote_plugin_url(url):
                result['errors'].append(f"无效的远程插件URL: {url}")
                return result
            
            # 从URL提取文件名
            filename = self._extract_filename_from_url(url)
            if not filename:
                result['errors'].append(f"无法从URL提取文件名: {url}")
                return result
            
            # 判断是zip文件还是单个Python文件
            if filename.endswith('.zip'):
                # 处理zip文件
                return self._handle_zip_file(url, filename, force_download)
            elif filename.endswith('.py'):
                # 处理单个Python文件
                return self._handle_python_file(url, filename, force_download)
            else:
                result['errors'].append(f"不支持的文件类型: {filename}")
                return result
            
        except Exception as e:
            result['errors'].append(f"下载插件时发生错误: {str(e)}")
            logger.error(f"下载插件失败: {str(e)}")
        
        return result
    
    def _extract_filename_from_url(self, url: str) -> Optional[str]:
        """从URL中提取文件名"""
        try:
            parsed_url = urlparse(url)
            path = parsed_url.path
            filename = os.path.basename(path)
            
            # 如果URL中没有文件名，尝试从查询参数中获取
            if not filename or filename == '':
                query_params = parsed_url.query
                if query_params:
                    # 尝试从查询参数中提取文件名
                    for param in query_params.split('&'):
                        if '=' in param:
                            key, value = param.split('=', 1)
                            if key.lower() in ['file', 'filename', 'name']:
                                filename = value
                                break
            
            # 如果还是没有文件名，使用默认名称
            if not filename or filename == '':
                filename = f"remote_plugin_{hash(url) % 10000}.zip"
            
            return filename
        except Exception as e:
            logger.error(f"提取文件名失败: {str(e)}")
            return None
    
    def _download_file(self, url: str, filename: str) -> Dict[str, Any]:
        """下载文件到临时目录"""
        result = {
            'success': False,
            'downloaded_path': None,
            'errors': []
        }
        
        try:
            # 创建临时目录
            temp_dir = tempfile.mkdtemp()
            downloaded_path = os.path.join(temp_dir, filename)
            
            # 下载文件
            logger.info(f"正在下载: {url}")
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            # 检查文件大小
            content_length = response.headers.get('content-length')
            if content_length:
                file_size = int(content_length)
                if file_size > 100 * 1024 * 1024:  # 100MB限制
                    result['errors'].append("文件过大，超过100MB限制")
                    return result
            
            # 保存文件
            with open(downloaded_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            result['success'] = True
            result['downloaded_path'] = downloaded_path
            
        except requests.exceptions.RequestException as e:
            result['errors'].append(f"下载文件失败: {str(e)}")
        except Exception as e:
            result['errors'].append(f"保存文件失败: {str(e)}")
        
        return result
    
    def _extract_zip_file(self, zip_path: str, extract_path: Path) -> Dict[str, Any]:
        """智能解压zip文件：解压到同名文件夹，处理嵌套目录，移动子文件夹"""
        result = {
            'success': False,
            'errors': [],
            'file_count': 0
        }
        
        try:
            # 如果目标目录已存在，先删除
            if extract_path.exists():
                shutil.rmtree(extract_path)
            
            # 创建目标目录
            extract_path.mkdir(parents=True, exist_ok=True)
            
            # 解压到目标目录
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                if not file_list:
                    result['errors'].append("ZIP文件为空")
                    return result
                
                logger.info(f"ZIP文件包含 {len(file_list)} 个文件/目录")
                for file_name in file_list:
                    logger.debug(f"  - {file_name}")
                
                # 检查是否有恶意文件路径
                for file_name in file_list:
                    if self._is_malicious_path(file_name):
                        result['errors'].append(f"检测到恶意文件路径: {file_name}")
                        return result
                
                # 解压到目标目录
                zip_ref.extractall(extract_path)
                
                # 智能处理解压后的目录结构
                self._smart_organize_extracted_content(extract_path)
                
                result['success'] = True
                result['file_count'] = len(file_list)
                
        except Exception as e:
            result['errors'].append(f"解压失败: {str(e)}")
            logger.error(f"解压失败: {str(e)}")
        
        return result
    
    def _smart_organize_extracted_content(self, extract_path: Path) -> None:
        """智能整理解压后的内容：处理嵌套目录，移动子文件夹"""
        try:
            # 获取plugin目录
            plugin_dir = extract_path.parent
            
            # 检查是否有嵌套的同名目录
            nested_dir = extract_path / extract_path.name
            if nested_dir.exists() and nested_dir.is_dir():
                logger.info(f"检测到嵌套目录: {nested_dir}")
                # 将嵌套目录中的内容移动到外层
                self._move_contents_up(nested_dir, extract_path)
                # 删除空的嵌套目录
                nested_dir.rmdir()
                logger.info(f"已平铺嵌套目录内容")
            
            # 检查是否有多个一级子文件夹
            subfolders = [item for item in extract_path.iterdir() if item.is_dir()]
            if len(subfolders) > 1:
                logger.info(f"检测到多个子文件夹: {[f.name for f in subfolders]}")
                # 将子文件夹移动到plugin目录
                for subfolder in subfolders:
                    target_path = plugin_dir / subfolder.name
                    if target_path.exists():
                        shutil.rmtree(target_path)
                    shutil.move(str(subfolder), str(target_path))
                    logger.info(f"移动子文件夹: {subfolder.name} -> {target_path}")
                
                # 如果extract_path为空，删除它
                if not any(extract_path.iterdir()):
                    extract_path.rmdir()
                    logger.info(f"删除空目录: {extract_path}")
            
        except Exception as e:
            logger.error(f"智能整理目录失败: {str(e)}")
    
    def _move_contents_up(self, source_dir: Path, target_dir: Path) -> None:
        """将源目录中的所有内容移动到目标目录"""
        try:
            for item in source_dir.iterdir():
                target_path = target_dir / item.name
                
                # 如果目标路径已存在，先删除
                if target_path.exists():
                    if target_path.is_file():
                        target_path.unlink()
                    else:
                        shutil.rmtree(target_path)
                
                # 移动文件或目录
                shutil.move(str(item), str(target_path))
                
            logger.info(f"已将 {source_dir} 中的内容移动到 {target_dir}")
            
        except Exception as e:
            logger.error(f"移动内容失败: {str(e)}")
    
    def _is_malicious_path(self, file_path: str) -> bool:
        """检查是否为恶意文件路径"""
        # 只检测路径遍历和绝对路径
        if file_path.startswith('/') or file_path.startswith('\\'):
            return True
        parts = file_path.replace('\\', '/').split('/')
        if '..' in parts:
            return True
        return False
    
    def list_remote_plugins(self) -> List[Dict[str, Any]]:
        """列出已下载的远程插件"""
        remote_plugins = []
        
        try:
            for item in self.plugin_dir.iterdir():
                if item.is_dir():
                    # 检查是否为远程插件（通过检查是否有特定的标记文件）
                    plugin_info = {
                        'name': item.name,
                        'path': str(item),
                        'is_remote': self._is_remote_plugin(item)
                    }
                    remote_plugins.append(plugin_info)
        except Exception as e:
            logger.error(f"列出远程插件失败: {str(e)}")
        
        return remote_plugins
    
    def _is_remote_plugin(self, plugin_path: Path) -> bool:
        """判断是否为远程插件"""
        # 可以通过检查特定的标记文件来判断
        # 这里简单判断目录名是否包含remote_plugin
        return 'remote_plugin' in plugin_path.name
    
    def remove_remote_plugin(self, plugin_name: str) -> Dict[str, Any]:
        """删除远程插件"""
        result = {
            'success': False,
            'errors': []
        }
        
        try:
            plugin_path = self.plugin_dir / plugin_name
            
            if not plugin_path.exists():
                result['errors'].append(f"插件不存在: {plugin_name}")
                return result
            
            if not plugin_path.is_dir():
                result['errors'].append(f"不是有效的插件目录: {plugin_name}")
                return result
            
            # 删除插件目录
            shutil.rmtree(plugin_path)
            result['success'] = True
            
            logger.info(f"远程插件删除成功: {plugin_name}")
            
        except Exception as e:
            result['errors'].append(f"删除插件失败: {str(e)}")
            logger.error(f"删除插件失败: {str(e)}")
        
        return result
    
    def cleanup_temp_files(self):
        """清理临时文件"""
        try:
            # 清理可能的临时目录
            temp_dir = tempfile.gettempdir()
            for item in os.listdir(temp_dir):
                if item.startswith('tmp') and os.path.isdir(os.path.join(temp_dir, item)):
                    try:
                        shutil.rmtree(os.path.join(temp_dir, item))
                    except:
                        pass
        except Exception as e:
            logger.warning(f"清理临时文件失败: {str(e)}")
    
    def _handle_zip_file(self, url: str, filename: str, force_download: bool) -> Dict[str, Any]:
        """处理zip文件下载和解压"""
        result = {
            'success': False,
            'downloaded_path': None,
            'extracted_path': None,
            'errors': [],
            'warnings': []
        }
        
        # 检查是否已存在
        extracted_path = self.plugin_dir / filename.replace('.zip', '')
        if extracted_path.exists() and not force_download:
            result['warnings'].append(f"插件已存在: {extracted_path}")
            result['success'] = True
            result['extracted_path'] = str(extracted_path)
            return result
        
        # 下载文件
        logger.info(f"开始下载远程插件: {url}")
        download_result = self._download_file(url, filename)
        
        if not download_result['success']:
            result['errors'].extend(download_result['errors'])
            return result
        
        downloaded_path = download_result['downloaded_path']
        result['downloaded_path'] = downloaded_path
        
        # 解压文件
        logger.info(f"开始解压插件: {downloaded_path}")
        extract_result = self._extract_zip_file(downloaded_path, extracted_path)
        
        if not extract_result['success']:
            result['errors'].extend(extract_result['errors'])
            # 清理下载的文件
            if os.path.exists(downloaded_path):
                os.remove(downloaded_path)
            return result
        
        result['success'] = True
        result['extracted_path'] = str(extracted_path)
        
        # 清理下载的zip文件
        if os.path.exists(downloaded_path):
            os.remove(downloaded_path)
        
        logger.info(f"远程插件下载并解压成功: {extracted_path}")
        return result
    
    def _handle_python_file(self, url: str, filename: str, force_download: bool) -> Dict[str, Any]:
        """处理单个Python文件下载"""
        result = {
            'success': False,
            'downloaded_path': None,
            'extracted_path': None,
            'errors': [],
            'warnings': []
        }
        
        # 检查是否已存在
        extracted_path = self.plugin_dir / filename
        if extracted_path.exists() and not force_download:
            result['warnings'].append(f"插件已存在: {extracted_path}")
            result['success'] = True
            result['extracted_path'] = str(extracted_path)
            return result
        
        # 下载文件
        logger.info(f"开始下载远程Python插件: {url}")
        download_result = self._download_file(url, filename)
        
        if not download_result['success']:
            result['errors'].extend(download_result['errors'])
            return result
        
        downloaded_path = download_result['downloaded_path']
        result['downloaded_path'] = downloaded_path
        
        # 移动文件到plugin目录
        try:
            # 确保plugin目录存在
            self.plugin_dir.mkdir(parents=True, exist_ok=True)
            
            # 移动文件
            shutil.move(downloaded_path, extracted_path)
            
            result['success'] = True
            result['extracted_path'] = str(extracted_path)
            
            logger.info(f"远程Python插件下载成功: {extracted_path}")
            
        except Exception as e:
            result['errors'].append(f"移动文件失败: {str(e)}")
            # 清理下载的文件
            if os.path.exists(downloaded_path):
                os.remove(downloaded_path)
        
        return result 