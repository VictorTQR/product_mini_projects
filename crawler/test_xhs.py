import json

from src.xhs import XHSCrawler

async def test_xhs_crawler_catch_item_content():
    crawler = XHSCrawler()
    await crawler.start()

    url = "https://www.xiaohongshu.com/explore/694575f6000000000d03fbea?xsec_token=ABfLwsYVLTNNitC38CcuFMf3yySrew9dl_QqCpRrjrTr8=&xsec_source=pc_feed"
    res = await crawler.catch_item_content(url)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    await crawler.close()

async def use_xhs_crawler(keyword: str, save_file: str = None):
    crawler = XHSCrawler()
    await crawler.start()
    res = await crawler.search(keyword)
    
    datas = []
    for item in res:
        data = await crawler.catch_item_content(item["url"])
        datas.append(data)

        await asyncio.sleep(2)
    
    if save_file:
        with open(save_file, "w", encoding="utf-8") as f:
            for data in datas:
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
    await crawler.close()

if __name__ == "__main__":
    import asyncio
    # asyncio.run(test_xhs_crawler())
    import sys
    keyword = sys.argv[1]
    asyncio.run(use_xhs_crawler(keyword, f"./data/xhs_{keyword}.jsonl"))
