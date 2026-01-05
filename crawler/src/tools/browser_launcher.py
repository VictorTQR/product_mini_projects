import asyncio
import socket
import httpx
from playwright.async_api import async_playwright, Browser, BrowserContext
from typing import Optional
from loguru import logger



class ManualChromeConnector:
    """连接已手动启动的Chrome浏览器"""

    def __init__(self, debug_port: int = 9222):
        self.debug_port = debug_port
        self.browser: Optional[Browser] = None
        self.playwright = None

    async def check_chrome_running(self) -> bool:
        """检查Chrome是否在指定端口运行"""
        logger.info(f"检查端口 {self.debug_port} 是否有Chrome运行...")

        try:
            # 尝试TCP连接
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)
                result = s.connect_ex(('localhost', self.debug_port))

                if result == 0:
                    logger.info(f"✅ 端口 {self.debug_port} 有进程在监听")

                    # 验证是否是Chrome的CDP接口
                    try:
                        async with httpx.AsyncClient(timeout=3) as client:
                            response = await client.get(
                                f"http://localhost:{self.debug_port}/json/version"
                            )

                            if response.status_code == 200:
                                data = response.json()
                                browser = data.get('Browser', '')
                                logger.info(f"✅ 确认是Chrome: {browser}")
                                return True
                            else:
                                logger.warning(f"⚠️  端口被占用但不是Chrome")
                                return False
                    except Exception as e:
                        logger.warning(f"⚠️  无法验证Chrome: {e}")
                        return False
                else:
                    logger.error(f"❌ 端口 {self.debug_port} 无响应")
                    return False

        except Exception as e:
            logger.error(f"❌ 检查端口失败: {e}")
            return False

    async def get_websocket_url(self) -> str:
        """获取CDP WebSocket URL"""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"http://localhost:{self.debug_port}/json/version"
                )

                if response.status_code == 200:
                    data = response.json()
                    ws_url = data.get("webSocketDebuggerUrl")

                    if ws_url:
                        logger.info(f"✅ 获取WebSocket URL成功")
                        logger.debug(f"   {ws_url}")
                        return ws_url
                else:
                    raise RuntimeError(f"HTTP {response.status_code}")

        except Exception as e:
            raise RuntimeError(f"获取WebSocket URL失败: {e}")

    async def connect(self, stealth_script: Optional[str] = None) -> BrowserContext:
        """
        连接到已启动的Chrome

        Args:
            stealth_script: 反检测脚本路径 (可选)

        Returns:
            BrowserContext: 浏览器上下文
        """
        # 1. 检查Chrome是否运行
        if not await self.check_chrome_running():
            raise RuntimeError(
                f"Chrome未在端口 {self.debug_port} 上运行!\n"
                f"请先手动启动Chrome，运行以下命令:\n"
                f'   chrome.exe --remote-debugging-port={self.debug_port}'
            )

        # 2. 获取WebSocket URL
        ws_url = await self.get_websocket_url()

        # 3. 连接Playwright
        logger.info("正在通过Playwright连接Chrome...")

        self.playwright = async_playwright()
        playwright_instance = await self.playwright.__aenter__()

        self.browser = await playwright_instance.chromium.connect_over_cdp(ws_url)

        if not self.browser.is_connected():
            raise RuntimeError("CDP连接失败")

        logger.info("✅ 成功连接到Chrome")

        # 4. 获取或创建上下文
        contexts = self.browser.contexts

        if contexts:
            context = contexts[0]
            logger.info("✅ 使用现有浏览器上下文")
        else:
            context = await self.browser.new_context(
                viewport={"width": 1920, "height": 1080},
                accept_downloads=True,
            )
            logger.info("✅ 创建新的浏览器上下文")

        # 5. 注入反检测脚本 (可选)
        if stealth_script:
            try:
                await context.add_init_script(path=stealth_script)
                logger.info(f"✅ 已注入反检测脚本: {stealth_script}")
            except Exception as e:
                logger.warning(f"⚠️  注入反检测脚本失败: {e}")

        return context

    async def close(self):
        """断开连接 (不关闭Chrome)"""
        logger.info("断开Chrome连接...")

        if self.browser:
            try:
                await asyncio.wait_for(self.browser.close(), timeout=5)
                logger.info("✅ 已断开连接 (Chrome仍在运行)")
            except Exception as e:
                logger.warning(f"⚠️  断开连接时出错: {e}")
            finally:
                self.browser = None

        if self.playwright:
            try:
                await asyncio.wait_for(
                    self.playwright.__aexit__(None, None, None),
                    timeout=5
                )
            except Exception as e:
                logger.warning(f"⚠️  关闭playwright时出错: {e}")
            finally:
                self.playwright = None

    # 支持async context manager
    async def __aenter__(self):
        return await self.connect()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
