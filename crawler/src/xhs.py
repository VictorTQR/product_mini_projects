import asyncio
from loguru import logger
import asyncio
import time

from playwright.async_api import expect

from .base import BaseCrawler
from .tools.browser_launcher import ManualChromeConnector

class XHSCrawler(BaseCrawler):
    """小红书爬虫"""
    def __init__(self, base_url: str = "https://www.xiaohongshu.com"):
        self.base_url = base_url
        self.context = None
        self.page = None
        self.connector = None

    async def start(self):
        """启动浏览器"""
        self.connector = ManualChromeConnector()
        context = await self.connector.connect()
        
        self.context = context
        self.page = await self.context.new_page()
        await self.page.goto(self.base_url)

    async def search(self, query: str, max_results: int = 50):
        """搜索小红书"""
        search_input = await self.page.query_selector("input#search-input")
        await search_input.fill(query)
        await search_input.press("Enter")

        # 等待搜索结果加载完成
        await self.page.wait_for_selector("section.note-item")
        await asyncio.sleep(3)

        # await self.page.locator("div.feeds-page").evaluate("el => el.scrollTop = 2000")
        # await asyncio.sleep(5)
        # exit()

        # 整理搜集结果
        search_results = await self.page.locator("section.note-item").all()
        logger.info(f"共找到 {len(search_results)} 条结果")

        filter_search_results = []
        for item in search_results:
            if await item.locator("div.query-note-list").count() > 0:
                continue
            filter_search_results.append(item)
        logger.info(f"过滤后共找到 {len(filter_search_results)} 条结果")

        results = []
        for idx, item in enumerate(filter_search_results):
            logger.info(f"处理第 {idx+1} 条结果")
            try:
                note_url = await item.locator("a.cover.mask").get_attribute("href", timeout=2000)
                footer = item.locator("div.footer")
                author = await footer.locator("div.name").inner_text()
                date = await footer.locator("div.time").inner_text()
                logger.info(f"找到笔记URL: {note_url}, 作者: {author}, 发布时间: {date}")
            except Exception as e:
                logger.error(f"处理第 {idx+1} 条结果时出错: {e}")
                continue

            if note_url:
                results.append({
                    "url": self.base_url + note_url,
                    "author": author,
                    "date": date
                })

        return results

    async def catch_item_content(self, note_url: str):
        """捕获笔记内容"""
        await self.page.goto(note_url)
        await self.page.wait_for_selector("div.note-content")

        # id
        

        # 媒体
        media_swipers = await self.page.locator("div.swiper-slide").all()
        media_contents = []
        for swiper in media_swipers:
            img_url = await swiper.locator("img").first.get_attribute("src")
            media_contents.append(img_url)
        media_contents = list(set(media_contents))

        # 内容
        content = await self.page.locator("div.note-content").inner_text()

        # 评论
        comments = []
        # 1. 定位评论容器和核心滚动容器
        scroll_container = self.page.locator("div.note-scroller")
        comment_container = self.page.locator(".comments-container")
        # 2. 定位无评论提示
        no_comment = self.page.locator("div.no-comments")
        if await no_comment.is_visible():
            logger.info("该笔记暂无评论")
        else:
            # 3. 定位结束标志（终止条件）
            end_flag = self.page.locator(".end-container")
            # 匀速滚动配置（可调整）
            scroll_step = 500  # 每次滚动步长（px），越小越顺滑
            scroll_interval = 0.5  # 每次滚动间隔（s），越小速度越快
            max_scroll_times = 50  # 最大滚动次数，防死循环
            scroll_count = 0
            # 滚动获取所有评论
            while True:
                # 终止条件1：end-container已出现
                if await end_flag.is_visible():
                    logger.info(f"✅ 已滚动到评论底部（出现end-container），共滚动 {scroll_count} 次")
                    break
                # 终止条件2：达到最大滚动次数
                if scroll_count >= max_scroll_times:
                    logger.warning(f"⚠️  达到最大滚动次数 {max_scroll_times}，停止滚动")
                    break

                # 核心：匀速滚动当前容器（只滚comments-container，不滚页面）
                await scroll_container.evaluate(f"""
                    (element, step) => {{
                        // 匀速滚动：累加scrollTop，scrollTop是容器滚动条距离顶部的距离
                        element.scrollTop += step;
                        // 滚动后保持容器位置（可选）
                        element.scrollBehavior = 'smooth';
                    }}
                """, scroll_step)

                # 间隔时间，保证匀速
                time.sleep(scroll_interval)
                scroll_count += 1
            # 验证：确认end-container可见
            expect(end_flag).to_be_visible(timeout=3000)

            # 3. 提取所有评论
            comment_items = await comment_container.locator("div.comment-item").all()
            logger.info(f"共找到 {len(comment_items)} 条评论")

            for item in comment_items:
                comment = await item.locator("div.content").inner_text()
                comments.append(comment)

        return {
            "media": media_contents,
            "content": content,
            "comments": comments
        }

    async def close(self):
        """关闭浏览器连接"""
        if self.page:
            try:
                await self.page.close()
                logger.info("页面已关闭")
            except Exception as e:
                logger.warning(f"关闭页面失败: {e}")
        
        if self.connector:
            try:
                await self.connector.close()
                logger.info("浏览器连接已关闭")
            except Exception as e:
                logger.warning(f"关闭连接失败: {e}")
