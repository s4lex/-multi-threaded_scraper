import queue
import threading
import time
from datetime import datetime
import requests
import os
from bs4 import BeautifulSoup
import re
import csv

THREADS_COUNT = 5
TOTAL_PAGES = 50
BASE_URL = 'https://books.toscrape.com/catalogue/page-{}.html'
OUTPUT_FILE = './books/books.csv'
OUTPUT_IMAGE_FILE = './books/images/'

q_results = queue.Queue()
q = queue.Queue()

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"
}


def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?<>":|]', '_', name)


def download_books(books, result_queue):
    books_data = []

    for book in books:
        name = book.h3.a['title']
        price = book.find('p', {'class': 'price_color'}).text.strip()
        rating_tag = book.find('p', {'class': 'star-rating'})
        rating = rating_tag['class'][1]

        img_tag = book.find('img')
        photo_relative = img_tag['src']
        photo_url = 'https://books.toscrape.com/' + photo_relative.replace('../', '')

        try:
            time.sleep(0.2)
            img_responce = requests.get(photo_url, headers=headers, timeout=10)
        except requests.exceptions.RequestException as e:
            print(f'Ошибка при запросе {photo_url}: {e}')
            continue

        # safe_name = sanitize_filename(name)[:100]
        # image_filename = os.path.join('./books/images', safe_name + '.jpg')

        image_filename = ''
        if img_responce.status_code == 200:

            safe_name = sanitize_filename(name)[:100]
            image_filename = os.path.join('./books/images', safe_name + '.jpg')
            with open(image_filename, 'wb') as f:
                f.write(img_responce.content)

        books_data.append({
            'name': name,
            'price': price,
            'rating': rating,
            'photo_url': photo_url,
            'local_image_path': image_filename
        })

    result_queue.put(books_data)


def parse_books(response, result_queue) -> None:
    soup = BeautifulSoup(response.text, 'html.parser')
    books = soup.find_all('article', {'class': 'product_pod'})
    download_books(books, result_queue)


def worker_th(task_queue, result_queue):
    while True:
        try:
            url = task_queue.get_nowait()
        except queue.Empty:
            break
        try:
            time.sleep(0.2)
            response = requests.get(url, headers=headers, timeout=10)
            response.encoding = 'utf-8'
            parse_books(response, result_queue)
        except requests.exceptions.Timeout as e:
            print(f'Ошибка при запросе {url}: {e}')
            continue


def main():
    os.makedirs(OUTPUT_IMAGE_FILE, exist_ok=True)

    threads = []

    for thread in range(THREADS_COUNT):
        threads.append(threading.Thread(target=worker_th, args=(q, q_results,)))

    for i in range(1, TOTAL_PAGES+1):
        q.put(BASE_URL.format(i))

    start_time = datetime.now()
    for th in threads:
        th.start()
    for th in threads:
        th.join()

    elapsed = datetime.now() - start_time

    columns = ['name', 'price', 'rating', 'photo_url', 'local_image_path']

    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8-sig') as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        while not q_results.empty():
            res = q_results.get()
            writer.writerows(res)
        print('Запись окончена')


    print(f'Время выполнения: {elapsed}')


if __name__ == '__main__':
    main()

