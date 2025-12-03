import requests
from lxml import etree
import csv
import time

def get_text(list_obj):
    return list_obj[0].strip() if list_obj else ''

def scrape_ssr1(output_csv='movie.csv'):
    base_url = 'https://ssr1.scrape.center/page/{}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36'
    }

    with open(output_csv, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        # 視你想抓哪些欄位，自訂 header
        writer.writerow(['Title', 'Types', 'Area', 'Length', 'ReleaseDate', 'Score'])

        for page in range(1, 11):  # 共 10 頁
            url = base_url.format(page)
            resp = requests.get(url, headers=headers)
            resp.encoding = resp.apparent_encoding  # 避免亂碼
            html = etree.HTML(resp.text)
            # 每個電影卡片
            nodes = html.xpath('//*[@id="index"]/div[1]/div[1]/div')
            for node in nodes:
                title = get_text(node.xpath('.//div[2]/a/h2/text()'))
                types = node.xpath('.//div[2]/div[1]//button/span/text()')
                types = '、'.join([t.strip() for t in types if t.strip()])
                area = get_text(node.xpath('.//div[2]/div[2]/span[1]/text()'))
                length = get_text(node.xpath('.//div[2]/div[2]/span[3]/text()'))
                release = get_text(node.xpath('.//div[2]/div[3]/span/text()'))
                score = get_text(node.xpath('.//div[3]/p[1]/text()'))
                writer.writerow([title, types, area, length, release, score])

            time.sleep(1)  # 禮貌等待，避免過快
    print(f"Saved to {output_csv}")

if __name__ == '__main__':
    scrape_ssr1()
