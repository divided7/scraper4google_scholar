# scraper4google_scholar
爬取google scholar搜索结果，并尝试下载。（在AI领域通常可以下载到）

环境:
```bash
pip install bs4
```
使用:
```
python google_scholar.py --search "attention is all you need" --num "10"
```
搜索结果将保存到csv中，可下载的pdf会下载至pdfs文件夹.
