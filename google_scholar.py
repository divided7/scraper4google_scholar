import requests
from bs4 import BeautifulSoup
import time
import urllib.parse
import csv
import argparse
import os
import re

def opt():
    parser = argparse.ArgumentParser()
    parser.add_argument("--search", type=str, default="attention is all you need")
    parser.add_argument("--num", type=int, default=10)
    return parser.parse_args()


class GoogleScholarScraper:
    def __init__(self):
        self.base_url = "https://scholar.google.com/scholar"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.64 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.google.com/',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def _parse_item(self, item):
        """解析单个搜索结果条目"""
        title_elem = item.find('h3', class_='gs_rt')
        title = None
        title_link = None
        if title_elem:
            a_tag = title_elem.find('a')
            if a_tag:
                title = a_tag.text
                title_link = a_tag['href']
            else:
                title = title_elem.text

        authors_elem = item.find('div', class_='gs_a')
        authors = authors_elem.text if authors_elem else ""

        snippet_elem = item.find('div', class_='gs_rs')
        snippet = snippet_elem.text.strip() if snippet_elem else ""

        cited_by = None
        pdf_link = None

        for a in item.find_all('a'):
            text = a.get_text()
            if 'Cited by' in text:
                try:
                    cited_by = int(text.replace('Cited by', '').strip())
                except ValueError:
                    cited_by = text.replace('Cited by', '').strip()
            if 'PDF' in text.upper():
                pdf_link = a.get('href')

        side_pdf = item.find_previous_sibling('div')
        if side_pdf:
            pdf_anchor = side_pdf.find('a')
            if pdf_anchor and 'pdf' in pdf_anchor.get('href', '').lower():
                pdf_link = pdf_anchor['href']

        return {
            'title': title,
            'title_link': title_link,
            'authors': authors,
            'snippet': snippet,
            'cited_by': cited_by,
            'pdf_link': pdf_link
        }

    def search(self, query, num_results=5):
        """执行搜索并返回结果"""
        results = []
        start = 0
        query = urllib.parse.quote_plus(query)

        while len(results) < num_results:
            params = {
                'q': query,
                'start': start,
                'hl': 'en'
            }

            try:
                response = self.session.get(self.base_url, params=params, timeout=10)
                response.raise_for_status()

                if 'sorry' in response.url or response.status_code != 200:
                    raise Exception("可能触发了反爬机制，请稍后再试或更换IP")

                soup = BeautifulSoup(response.text, 'html.parser')
                items = soup.find_all('div', class_='gs_ri')

                if not items:
                    break

                for item in items:
                    if len(results) >= num_results:
                        break
                    results.append(self._parse_item(item))

                start += 10
                time.sleep(3)

            except Exception as e:
                print(f"请求失败: {str(e)}")
                break

        return results[:num_results]

    def save_to_csv(self, results, filename="results.csv"):
        """将结果保存到CSV文件"""
        with open(filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file,
                                    fieldnames=['title', 'title_link', 'authors', 'snippet', 'cited_by', 'pdf_link'])
            writer.writeheader()
            for result in results:
                writer.writerow(result)
        print(f"已保存 {len(results)} 条记录到 {filename}")

    def download_pdfs(self, results, folder="pdfs"):
        """下载所有 PDF 链接不为空的文件"""
        if not os.path.exists(folder):
            os.makedirs(folder)

        for idx, result in enumerate(results, 1):
            pdf_url = result.get('pdf_link')
            title = result.get('title') or f"paper_{idx}"
            if pdf_url:
                try:
                    safe_title = re.sub(r'[\\/*?:"<>|]', "_", title[:30])  # 清理非法字符
                    filename = f"{idx:02d}_{safe_title}.pdf"
                    filepath = os.path.join(folder, filename)

                    response = self.session.get(pdf_url, stream=True, timeout=15)
                    response.raise_for_status()

                    with open(filepath, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=1024):
                            if chunk:
                                f.write(chunk)

                    print(f"[✓] 下载成功: {filename}")
                except Exception as e:
                    print(f"[✗] 下载失败 ({title}): {str(e)}")

if __name__ == "__main__":
    args = opt()
    scraper = GoogleScholarScraper()
    results = scraper.search(args.search, args.num) # 搜索
    scraper.save_to_csv(results, f"{args.search}.csv") # 保存csv
    scraper.download_pdfs(results)
    for idx, result in enumerate(results, 1):
        print(f"结果 {idx}:")
        print(f"标题: {result['title']}")
        print(f"链接: {result['title_link']}")
        print(f"作者: {result['authors']}")
        print(f"摘要: {result['snippet']}")
        print(f"被引用数: {result['cited_by']}")
        print(f"PDF链接: {result['pdf_link']}")
        print("-" * 50)


