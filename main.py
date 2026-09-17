import queue
import threading
from datetime import datetime
import requests
import os
from bs4 import BeautifulSoup
import re


headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
}

def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?<>":|]', '_', name)


def download_books(books):
    books_data = []

    for book in books:
        name = book.h3.a['title']
        price = book.find('p', {'class': 'price_color'}).text.strip()
        rating_tag = book.find('p', {'class': 'star-rating'})
        rating = rating_tag['class'][1]

        img_tag = book.find('img')
        photo_relative = img_tag['src']
        photo_url = 'https://books.toscrape.com/' + photo_relative.replace('../', '')

        img_responce = requests.get(photo_url, headers=headers)

        if img_responce.status_code == 200:

            safe_name = sanitize_filename(name)[:100]
            image_filename = os.path.join('./books', safe_name + '.jpg')
            with open(image_filename, 'wb') as f:
                f.write(img_responce.content)

        books_data.append({
            'name': name,
            'price': price,
            'rating': rating,
        })

    q_results.put(books_data)


def parse_books(response) -> None:
    soup = BeautifulSoup(response.text, 'html.parser')
    books = soup.find_all('article', {'class': 'product_pod'})
    download_books(books)


def worker_th():
    while True:
        try:
            url = q.get_nowait()
        except queue.Empty:
            break
        response = requests.get(url, headers=headers)
        response.encoding = 'utf-8'
        parse_books(response)


links = []
q_results = queue.Queue()
q = queue.Queue()
def main():
    os.makedirs("./books", exist_ok=True)

    threads = []

    for thread in range(7):
        threads.append(threading.Thread(target=worker_th))

    for i in range(1, 51):
        q.put(f'https://books.toscrape.com/catalogue/page-{i}.html')

    start_time = datetime.now()
    for th in threads:
        th.start()
    for th in threads:
        th.join()

    while not q_results.empty():
        links.append(q_results.get())

    print(f'Время выполнения {datetime.now() - start_time}')




if __name__ == '__main__':
    main()

