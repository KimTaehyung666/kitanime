import requests
from bs4 import BeautifulSoup
import os
from flask import Flask, render_template, request, jsonify, redirect, url_for
from urllib.parse import urljoin, quote, urlparse
import re
import base64

app = Flask(__name__)
BASE_URL = "https://ww1.anoboy.boo/"
HEADERS = {"User-Agent": "Mozilla/5.0"}

class AnimeScraper:
    def __init__(self):
        self.base_url = BASE_URL
        
    def resolve_url(self, url):
        """Convert relative URL to absolute URL"""
        if url.startswith('//'):
            return 'https:' + url
        elif url.startswith('/'):
            return urljoin(self.base_url, url)
        elif url.startswith('http'):
            return url
        else:
            return urljoin(self.base_url, url)
        
    def get_anime_list(self, page=1):
        """Get anime list with cover images"""
        url = BASE_URL if page == 1 else f"{BASE_URL}page/{page}/"
        try:
            r = requests.get(url, headers=HEADERS)
            soup = BeautifulSoup(r.text, "html.parser")
            
            anime_list = []
            anime_links = soup.find_all('a', href=re.compile(r'/202[0-9]/'))
            
            for link in anime_links:
                amv_div = link.find('div', class_='amv')
                if amv_div:
                    title_div = amv_div.find('h3', class_='ibox1')
                    jam_div = amv_div.find('div', class_='jamup')
                    img = amv_div.find('img')
                    
                    if title_div and link.get('href'):
                        cover_url = ""
                        if img and img.get('src'):
                            cover_url = self.resolve_url(img['src'])

                        raw_title = title_div.text.strip()
                        base_title, episode = self.extract_episode(raw_title)
                        clean_title = self.clean_title(base_title)

                        anime_data = {
                            "title": clean_title,
                            "episode": episode,
                            "jam": jam_div.text.strip() if jam_div else "Unknown",
                            "link": link['href'],
                            "cover": cover_url
                        }
                        if not any(a['title'] == anime_data['title'] for a in anime_list):
                            anime_list.append(anime_data)
            
            return anime_list[:20]
        except Exception:
            return []
    
    def clean_title(self, title):
        """Bersihkan judul dari karakter aneh dan rapikan"""
        title = re.sub(r'[^\w\s\-\.\,\!\(\)]', '', title)
        title = re.sub(r'\s+', ' ', title)
        if len(title) > 50:
            title = title[:47] + '...'
        return title.strip()

    @staticmethod
    def extract_episode(title):
        """Pisahkan nomor episode dari judul.

        'Kore Kaite Shine Episode 1' -> ('Kore Kaite Shine', '1')
        Mengembalikan (judul_tanpa_episode, nomor_episode). Nomor '' jika tidak ada.
        """
        t = title.strip()
        m = re.search(r'\s*[-–]?\s*Episode\s*(\d+(?:\.\d+)?)\s*$', t, re.IGNORECASE)
        if not m:
            m = re.search(r'\s*[-–]?\s*Eps?\.?\s*(\d+(?:\.\d+)?)\s*$', t, re.IGNORECASE)
        if m:
            return t[:m.start()].strip(), m.group(1)
        return t, ""


    def search_anime(self, keyword, page=1):
        """Search anime from anoboy search"""
        try:
            if page == 1:
                search_url = f"{BASE_URL}?s={quote(keyword.replace(' ', '+'))}"
            else:
                search_url = f"{BASE_URL}page/{page}/?s={quote(keyword.replace(' ', '+'))}"
            
            r = requests.get(search_url, headers=HEADERS)
            
            if r.status_code != 200:
                return []
                
            soup = BeautifulSoup(r.text, "html.parser")
            results = []
            
            amv_divs = soup.find_all('div', class_='amv')
            
            for amv_div in amv_divs:
                link = amv_div.find_parent('a', href=True)
                if link and link.get('href'):
                    href = link['href']
                    if any(pattern in href for pattern in ['/201', '/202', '/anime', '/one-punch']):
                        title_div = amv_div.find('h3', class_='ibox1')
                        jam_div = amv_div.find('div', class_='jamup')
                        img = amv_div.find('img')
                        
                        if title_div:
                            cover_url = ""
                            if img and img.get('src'):
                                cover_url = self.resolve_url(img['src'])
                            
                            clean_title = self.clean_title(title_div.text.strip())
                            
                            anime_data = {
                                "title": clean_title,
                                "jam": jam_div.text.strip() if jam_div else "Unknown",
                                "link": href,
                                "cover": cover_url
                            }
                            
                            if not any(a['link'] == anime_data['link'] for a in results):
                                results.append(anime_data)
            
            if not results:
                column_content = soup.find('div', class_='column-content')
                if column_content:
                    links = column_content.find_all('a', href=True)
                    for link in links:
                        href = link.get('href', '')
                        if any(pattern in href for pattern in ['/201', '/202', '/anime', '/one-punch']):
                            amv_div = link.find('div', class_='amv')
                            if amv_div:
                                title_div = amv_div.find('h3', class_='ibox1')
                                jam_div = amv_div.find('div', class_='jamup')
                                img = amv_div.find('img')
                                
                                if title_div:
                                    cover_url = ""
                                    if img and img.get('src'):
                                        cover_url = self.resolve_url(img['src'])
                                    
                                    clean_title = self.clean_title(title_div.text.strip())
                                    
                                    anime_data = {
                                        "title": clean_title,
                                        "jam": jam_div.text.strip() if jam_div else "Unknown",
                                        "link": href,
                                        "cover": cover_url
                                    }
                                    
                                    if not any(a['link'] == anime_data['link'] for a in results):
                                        results.append(anime_data)
            
            if not results:
                all_links = soup.find_all('a', href=True)
                for link in all_links:
                    href = link.get('href', '')
                    if ('one-punch' in href.lower() or 
                        any(pattern in href for pattern in ['/201', '/202', 'anoboy.boo/201', 'anoboy.boo/202'])):
                        
                        amv_div = link.find('div', class_='amv')
                        if not amv_div:
                            parent = link.parent
                            if parent:
                                amv_div = parent.find('div', class_='amv')
                        
                        if amv_div:
                            title_div = amv_div.find('h3', class_='ibox1')
                            jam_div = amv_div.find('div', class_='jamup')
                            img = amv_div.find('img')
                            
                            if title_div:
                                cover_url = ""
                                if img and img.get('src'):
                                    cover_url = self.resolve_url(img['src'])
                                
                                clean_title = self.clean_title(title_div.text.strip())
                                
                                anime_data = {
                                    "title": clean_title,
                                    "jam": jam_div.text.strip() if jam_div else "Unknown",
                                    "link": href,
                                    "cover": cover_url
                                }
                                
                                if not any(a['link'] == anime_data['link'] for a in results):
                                    results.append(anime_data)
            
            return results
            
        except Exception:
            return []

    def get_movie_list(self, page=1):
        """Get anime movie list"""
        try:
            if page == 1:
                url = f"{BASE_URL}category/anime-movie/"
            else:
                url = f"{BASE_URL}category/anime-movie/page/{page}/"
            
            r = requests.get(url, headers=HEADERS)
            soup = BeautifulSoup(r.text, "html.parser")
            
            movie_list = []
            column_content = soup.find('div', class_='column-content')
            if column_content:
                movie_links = column_content.find_all('a', href=re.compile(r'/202[0-9]/'))
                
                for link in movie_links:
                    amv_div = link.find('div', class_='amv')
                    if amv_div:
                        title_div = amv_div.find('h3', class_='ibox1')
                        jam_div = amv_div.find('div', class_='jamup')
                        img = amv_div.find('img')
                        
                        if title_div and link.get('href'):
                            cover_url = ""
                            if img and img.get('src'):
                                cover_url = self.resolve_url(img['src'])
                            
                            clean_title = self.clean_title(title_div.text.strip())
                            
                            movie_data = {
                                "title": clean_title,
                                "jam": jam_div.text.strip() if jam_div else "Unknown",
                                "link": link['href'],
                                "cover": cover_url,
                                "type": "movie"
                            }
                            
                            if not any(m['link'] == movie_data['link'] for m in movie_list):
                                movie_list.append(movie_data)
            
            return movie_list[:20]
        except Exception:
            return []

    def get_category_list(self, category_slug, page=1):
        """Get anime list by category slug (genre, live-action, tokusatsu, dll)"""
        try:
            # Ongoing punya URL khusus
            if category_slug == 'ongoing':
                if page == 1:
                    url = f"{BASE_URL}anime/ongoing/"
                else:
                    url = f"{BASE_URL}anime/ongoing/page/{page}/"
            else:
                if page == 1:
                    url = f"{BASE_URL}category/{category_slug}/"
                else:
                    url = f"{BASE_URL}category/{category_slug}/page/{page}/"

            r = requests.get(url, headers=HEADERS)
            soup = BeautifulSoup(r.text, "html.parser")

            result = []

            # Coba dari column-content dulu
            container = soup.find('div', class_='column-content') or soup.find('div', class_='home_index')

            links = []
            if container:
                links = container.find_all('a', href=re.compile(r'/(20[12][0-9]|anime)/'))
            if not links:
                links = soup.find_all('a', href=re.compile(r'/(20[12][0-9])/'))

            for link in links:
                amv_div = link.find('div', class_='amv')
                if not amv_div:
                    amv_div = link.find('div', id='amv')
                if amv_div:
                    title_div = amv_div.find('h3', class_='ibox1') or amv_div.find('h3', class_='ibox')
                    jam_div = amv_div.find('div', class_='jamup')
                    img = amv_div.find('img')

                    if title_div and link.get('href'):
                        cover_url = self.resolve_url(img['src']) if img and img.get('src') else ""
                        item = {
                            "title": self.clean_title(title_div.text.strip()),
                            "jam": jam_div.text.strip() if jam_div else "",
                            "link": link['href'],
                            "cover": cover_url
                        }
                        if not any(a['link'] == item['link'] for a in result):
                            result.append(item)

            return result[:24]
        except Exception:
            return []

    def get_schedule(self):
        """Ambil jadwal rilis anime dari halaman seasonal anoboy.

        Sumber (/uploads/jadwal.php) mengelompokkan anime per TIPE
        (TV New, TV Continuing, ONA, OVA, Movie, Special), bukan per hari.
        Method ini mengembalikan dua bentuk sekaligus:
          - "by_day":  dict {Senin..Minggu: [anime]} dihitung dari tanggal mulai
          - "by_type": list [{type, items:[anime]}] sesuai urutan sumber
        """
        DAYS = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
        empty = {"by_day": {d: [] for d in DAYS}, "by_type": [], "days": DAYS}
        try:
            url = urljoin(self.base_url, "uploads/jadwal.php")
            r = requests.get(url, headers=HEADERS, timeout=20)
            soup = BeautifulSoup(r.text, "html.parser")

            by_day = {d: [] for d in DAYS}
            by_type = []
            type_index = {}
            current_type = None

            # Telusuri header tipe dan blok anime sesuai urutan dokumen
            nodes = soup.find_all(
                'div',
                class_=lambda c: c and (
                    'anime-header' in c or 'js-anime-category-producer' in c
                )
            )

            for node in nodes:
                classes = node.get('class', [])

                if 'anime-header' in classes:
                    label = node.get_text(strip=True)
                    if label:
                        current_type = label
                        if label not in type_index:
                            type_index[label] = []
                            by_type.append({"type": label, "items": type_index[label]})
                    continue

                # Blok anime
                title_tag = node.find('a', class_='link-title')
                title = title_tag.get_text(strip=True) if title_tag else ""
                if not title:
                    continue

                img = node.find('img')
                cover = ""
                if img and img.get('src'):
                    cover = img['src']

                score_tag = node.find('span', class_='js-score')
                score = score_tag.get_text(strip=True) if score_tag else "0"
                try:
                    score = "" if float(score) == 0 else score
                except ValueError:
                    pass

                date_tag = node.find('span', class_='js-start_date')
                raw_date = date_tag.get_text(strip=True) if date_tag else ""
                weekday = self.weekday_from_yyyymmdd(raw_date)

                anime = {
                    "title": self.clean_title(title),
                    "cover": cover,
                    "score": score,
                    "start_date": self.format_start_date(raw_date),
                    "type": current_type or "Lainnya",
                    "day": weekday,
                    "search_q": self.title_to_query(title),
                }

                if current_type and current_type in type_index:
                    type_index[current_type].append(anime)
                if weekday:
                    by_day[weekday].append(anime)

            # Buang grup tanpa item (mis. banner musim "NEW SPRING ...")
            by_type = [g for g in by_type if g["items"]]

            return {"by_day": by_day, "by_type": by_type, "days": DAYS}
        except Exception:
            return empty

    @staticmethod
    def weekday_from_yyyymmdd(raw):
        """Ubah tanggal 'YYYYMMDD' jadi nama hari Indonesia. '' jika invalid."""
        DAYS = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
        if not raw or len(raw) != 8 or not raw.isdigit():
            return ""
        try:
            y, m, d = int(raw[:4]), int(raw[4:6]), int(raw[6:8])
            # Algoritma Sakamoto: 0=Minggu .. 6=Sabtu
            t = [0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4]
            yy = y - (1 if m < 3 else 0)
            w = (yy + yy // 4 - yy // 100 + yy // 400 + t[m - 1] + d) % 7
            # Petakan ke daftar Senin-first
            return DAYS[(w + 6) % 7]
        except (ValueError, IndexError):
            return ""

    @staticmethod
    def format_start_date(raw):
        """Ubah 'YYYYMMDD' jadi 'DD MMM YYYY' (Indonesia). '' jika invalid."""
        if not raw or len(raw) != 8 or not raw.isdigit():
            return ""
        MONTHS = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun",
                  "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
        try:
            y, m, d = raw[:4], int(raw[4:6]), int(raw[6:8])
            return f"{d:02d} {MONTHS[m - 1]} {y}"
        except (ValueError, IndexError):
            return ""

    @staticmethod
    def title_to_query(title):
        """Sederhanakan judul jadi keyword pencarian yang lebih cocok.

        Buang penanda season/part dan segala sesudah ':' agar hasil
        pencarian di anoboy lebih relevan (mis. 'Re:Zero ... 4th Season'
        -> 'Re Zero kara Hajimeru Isekai Seikatsu').
        """
        q = title.strip()
        # Buang penanda season/part di akhir judul
        q = re.sub(
            r'\s+(?:\d+(?:st|nd|rd|th)\s+season|season\s*\d+|part\s*\d+|'
            r'cour\s*\d+|final\s+season|\d+(?:st|nd|rd|th)\s+cour)\s*$',
            '', q, flags=re.IGNORECASE
        )
        # Rapikan tanda baca jadi spasi
        q = re.sub(r'[:~\-–—]', ' ', q)
        q = re.sub(r'\s+', ' ', q).strip()
        return q or title.strip()

    def get_home_movies(self):
        """Get featured movies from homepage sidebar"""
        try:
            r = requests.get(BASE_URL, headers=HEADERS)
            soup = BeautifulSoup(r.text, "html.parser")
            
            featured_movies = []
            
            sidebar = soup.find('div', class_='side_home')
            if sidebar:
                jdl_div = sidebar.find('h2', class_='jdl')
                if jdl_div and 'movie' in jdl_div.text.lower():
                    movie_links = sidebar.find_all('a', href=True)
                    
                    for link in movie_links:
                        if 'category' in link.get('href', ''):
                            continue
                            
                        amv_div = link.find('div', id='amv')
                        if amv_div:
                            img = amv_div.find('img')
                            title_div = amv_div.find('h3', class_='ibox')
                            
                            if title_div and link.get('href'):
                                cover_url = ""
                                if img and img.get('src'):
                                    cover_url = self.resolve_url(img['src'])
                                
                                clean_title = self.clean_title(title_div.text.strip())
                                
                                movie_data = {
                                    "title": clean_title,
                                    "link": link['href'],
                                    "cover": cover_url,
                                    "type": "movie"
                                }
                                
                                if not any(m['link'] == movie_data['link'] for m in featured_movies):
                                    featured_movies.append(movie_data)
            
            return featured_movies[:6]
        except Exception:
            return []

    def get_prev_next_episodes(self, current_url):
        """Get previous and next episode links - FIXED VERSION"""
        try:
            r = requests.get(current_url, headers=HEADERS)
            soup = BeautifulSoup(r.text, "html.parser")
            
            prev_next = {"prev": None, "next": None}
            
            # METHOD 1: Cari dari navigasi div dengan struktur yang lebih spesifik
            navigasi_div = soup.find('div', id='navigasi')
            if navigasi_div:
                # Cari semua link navigasi
                nav_links = navigasi_div.find_all('a', href=True)
                
                for link in nav_links:
                    href = link.get('href', '')
                    if not href or href == '#' or 'javascript' in href:
                        continue
                    
                    # Skip link iklan
                    if any(ad_domain in href for ad_domain in ['avenue56dancestudios.com', 'playbook88', 'ads']):
                        continue
                    
                    # Cek parent element untuk menentukan prev/next
                    parent = link.parent
                    if parent and 'widget-title' in parent.get('class', []):
                        parent_text = parent.get_text(strip=True).lower()
                        
                        # Deteksi prev episode
                        if any(keyword in parent_text for keyword in ['sebelum', 'previous', 'prev', 'fast-backward', '←']):
                            prev_next["prev"] = {
                                "url": self.resolve_url(href),
                                "title": link.get_text(strip=True) or "Episode Sebelumnya"
                            }
                        
                        # Deteksi next episode
                        elif any(keyword in parent_text for keyword in ['selanj', 'next', 'lanjut', 'fast-forward', '→']):
                            prev_next["next"] = {
                                "url": self.resolve_url(href),
                                "title": link.get_text(strip=True) or "Episode Selanjutnya"
                            }
            
            # METHOD 2: Cari berdasarkan struktur h3 widget-title langsung
            if not prev_next["prev"] and not prev_next["next"]:
                widget_titles = soup.find_all('h3', class_='widget-title')
                
                for widget in widget_titles:
                    widget_text = widget.get_text(strip=True).lower()
                    link = widget.find('a', href=True)
                    
                    if not link:
                        continue
                        
                    href = link.get('href', '')
                    if not href or any(ad_domain in href for ad_domain in ['avenue56dancestudios.com']):
                        continue
                    
                    # Deteksi berdasarkan icon dan text
                    icon = widget.find('i')
                    icon_classes = icon.get('class', []) if icon else []
                    
                    # Prev episode detection
                    if (any(keyword in widget_text for keyword in ['sebelum', 'previous', 'prev']) or
                        (icon and any(cls in icon_classes for cls in ['fa-fast-backward', 'fa-backward', 'fa-chevron-left']))):
                        prev_next["prev"] = {
                            "url": self.resolve_url(href),
                            "title": link.get_text(strip=True) or "Episode Sebelumnya"
                        }
                    
                    # Next episode detection  
                    elif (any(keyword in widget_text for keyword in ['selanj', 'next', 'lanjut']) or
                          (icon and any(cls in icon_classes for cls in ['fa-fast-forward', 'fa-forward', 'fa-chevron-right']))):
                        prev_next["next"] = {
                            "url": self.resolve_url(href),
                            "title": link.get_text(strip=True) or "Episode Selanjutnya"
                        }
            
            # METHOD 3: Fallback - cari dari season list
            if not prev_next["prev"] and not prev_next["next"]:
                seasons = self.extract_seasons_for_nav(soup)
                current_path = current_url.replace('https://ww1.anoboy.boo/', '')
                
                for season in seasons:
                    for i, episode in enumerate(season["episodes"]):
                        episode_path = episode["url"].replace('https://ww1.anoboy.boo/', '')
                        if episode_path == current_path:
                            # Previous episode
                            if i > 0:
                                prev_ep = season["episodes"][i-1]
                                prev_next["prev"] = {
                                    "url": prev_ep["url"],
                                    "title": prev_ep["title"]
                                }
                            
                            # Next episode
                            if i < len(season["episodes"]) - 1:
                                next_ep = season["episodes"][i+1]
                                prev_next["next"] = {
                                    "url": next_ep["url"], 
                                    "title": next_ep["title"]
                                }
                            break
            
            return prev_next
            
        except Exception as e:
            print(f"Error in get_prev_next_episodes: {e}")
            return {"prev": None, "next": None}

    def extract_seasons_for_nav(self, soup):
        """Extract seasons for navigation purpose"""
        seasons = []
        
        # Cari dari berbagai struktur yang mungkin
        episode_containers = [
            soup.find('ul', class_='lcp_catlist'),
            soup.find('div', class_='singlelink'),
            soup.find('div', class_='episode-list'),
            soup.find('div', class_='episodes')
        ]
        
        for container in episode_containers:
            if container:
                season_data = {
                    "name": "Episodes",
                    "episodes": []
                }
                
                # Cari semua link episode
                episode_links = container.find_all('a', href=True)
                for link in episode_links:
                    href = link.get('href', '')
                    link_text = link.get_text(strip=True).lower()
                    
                    # Filter hanya link episode
                    if (href and '/202' in href and 
                        any(keyword in link_text for keyword in ['episode', 'eps', 'ep', 'ep.'])):
                        season_data["episodes"].append({
                            "title": self.clean_title(link.get_text(strip=True)),
                            "url": href
                        })
                
                # Urutkan episode secara descending (terbaru dulu)
                if season_data["episodes"]:
                    season_data["episodes"].reverse()
                    seasons.append(season_data)
                    break
        
        return seasons

    def get_anime_detail(self, page_url):
        """Get detailed anime information - FIXED UNTUK MOVIE (NO BATCH DOWNLOAD)"""
        try:
            r = requests.get(page_url, headers=HEADERS)
            soup = BeautifulSoup(r.text, "html.parser")
            
            detail = {
                "title": "",
                "cover": "",
                "stream_links": [],
                "download_links": [],
                "batch_downloads": [],
                "single_episodes": [],
                "seasons": [],
                "episode_servers": [],
                "info": {},
                "description": ""
            }
            
            # EKSTRAKSI JUDUL
            title_tag = soup.find("h1")
            if title_tag:
                detail["title"] = self.clean_title(title_tag.text.strip())
            
            # EKSTRAKSI COVER
            sisi_div = soup.find("div", class_="sisi")
            if sisi_div:
                img = sisi_div.find("img")
                if img and img.get("src"):
                    detail["cover"] = self.resolve_url(img["src"])
                
                # EKSTRAKSI SINOPISIS DARI CONTENTDEKS - FIXED UNTUK MOVIE & SEASON
                contentdeks_div = sisi_div.find("div", class_="contentdeks")
                if contentdeks_div:
                    # Clone element untuk menghindari modifikasi original
                    contentdeks_clone = contentdeks_div.__copy__()
                    
                    # Hapus tag strong dari clone
                    for strong_tag in contentdeks_clone.find_all("strong"):
                        strong_tag.decompose()
                    
                    # Ambil teks sinopsis dari clone
                    sinopsis_text = contentdeks_clone.get_text(strip=True)
                    if sinopsis_text and len(sinopsis_text) > 50:
                        # FILTER KHUSUS UNTUK MOVIE DAN SEASON - HAPUS TEXT UPLOAD INFO
                        cleaned_text = self.clean_movie_season_description(sinopsis_text, detail["title"])
                        if cleaned_text:
                            detail["description"] = cleaned_text
            
            # FALLBACK 1: Jika tidak ada sinopsis yang valid, cari dari entry-content
            if not detail["description"]:
                entry_content = soup.find("div", class_="entry-content")
                if entry_content:
                    # Buat clone untuk menghindari modifikasi original
                    entry_clone = entry_content.__copy__()
                    
                    # Hapus elemen yang tidak diinginkan
                    for elem in entry_clone.find_all(["script", "style", "div", "table", "ul", "ol"]):
                        elem.decompose()
                    
                    entry_text = entry_clone.get_text(strip=True)
                    if entry_text and len(entry_text) > 100:
                        cleaned_text = self.clean_movie_season_description(entry_text, detail["title"])
                        if cleaned_text:
                            detail["description"] = cleaned_text
            
            # FALLBACK 2: Cari dari semua text di page yang panjang dan mengandung kata kunci sinopsis
            if not detail["description"]:
                all_text = soup.get_text()
                # Split by newlines dan cari paragraph yang panjang
                paragraphs = [p.strip() for p in all_text.split('\n') if len(p.strip()) > 150]
                
                for paragraph in paragraphs:
                    # Filter paragraph yang mengandung kata kunci sinopsis dan tidak mengandung kata kunci upload
                    if (any(keyword in paragraph.lower() for keyword in ['adalah', 'menceritakan', 'berkisah', 'serial', 'film', 'bercerita']) and
                        not any(keyword in paragraph.lower() for keyword in ['di unggah', 'terbit', 'wib', 'subtitle', 'sub indo', 'selamat menyaksikan'])):
                        
                        cleaned_text = self.clean_movie_season_description(paragraph, detail["title"])
                        if cleaned_text:
                            detail["description"] = cleaned_text
                            break
            
            # EKSTRAKSI INFORMASI DARI TABEL - FIXED UNTUK SEMUA TIPE
            info_found = False
            if sisi_div:
                contenttable_div = sisi_div.find("div", class_="contenttable")
                if contenttable_div:
                    table = contenttable_div.find("table")
                    if table:
                        for row in table.find_all("tr"):
                            cells = row.find_all(["th", "td"])
                            if len(cells) == 2:
                                key = cells[0].get_text(strip=True).replace(':', '')
                                value = cells[1].get_text(strip=True)
                                
                                # Bersihkan value dari link dan whitespace
                                value_clean = re.sub(r'\s+', ' ', value).strip()
                                value_clean = re.sub(r'<a[^>]*>.*?</a>', '', value_clean)
                                
                                # Simpan ke info dictionary
                                if key and value_clean:
                                    detail["info"][key] = value_clean
                                    info_found = True
            
            # FALLBACK: Jika tidak ada info dari tabel sisi, cari dari semua tabel di page
            if not info_found:
                all_tables = soup.find_all("table")
                for table in all_tables:
                    for row in table.find_all("tr"):
                        cells = row.find_all(["th", "td"])
                        if len(cells) == 2:
                            key = cells[0].get_text(strip=True).replace(':', '')
                            value = cells[1].get_text(strip=True)
                            value_clean = re.sub(r'\s+', ' ', value).strip()
                            value_clean = re.sub(r'<a[^>]*>.*?</a>', '', value_clean)
                            
                            # Filter keys yang umum untuk anime info
                            common_keys = ['judul', 'title', 'episodes', 'studio', 'source', 'durasi', 'duration', 'genre', 'score', 'rating', 'type', 'status']
                            if (key and value_clean and key.lower() in common_keys and 
                                key not in detail["info"]):
                                detail["info"][key] = value_clean
            
            # EKSTRAKSI STREAMING LINKS - FIXED UNTUK MULTIPLE QUALITY
            self.extract_streaming_servers(soup, detail)
            
            if not detail["stream_links"]:
                iframe = soup.find("iframe", id="mediaplayer")
                if iframe and iframe.get("src"):
                    stream_url = iframe["src"]
                    detail["stream_links"].append({
                        "provider": "Btube",
                        "url": self.resolve_url(stream_url),
                        "quality": "360p-720p"
                    })
            
            # EKSTRAKSI SEASONS
            self.extract_seasons(soup, detail)
            
            # EKSTRAKSI DOWNLOAD LINKS - UNTUK SEMUA TIPE
            download_section = soup.find("div", class_="download")
            if download_section:
                provider_links = {}
                for span in download_section.find_all("span", class_="ud"):
                    provider = span.find("span", class_="udj")
                    if provider:
                        provider_name = provider.text.strip()
                        links = span.find_all("a", class_="udl")
                        
                        for link in links:
                            if link.get("href") and link["href"] != "none" and not link["href"].startswith("javascript"):
                                quality = link.text.strip()
                                if provider_name not in provider_links:
                                    provider_links[provider_name] = []
                                provider_links[provider_name].append({
                                    "quality": quality,
                                    "url": link["href"]
                                })
                
                for provider_name, links in provider_links.items():
                    detail["download_links"].append({
                        "provider": provider_name,
                        "links": links,
                        "type": "single"
                    })
            
            # EKSTRAKSI BATCH DOWNLOADS - HANYA UNTUK SERIES, BUKAN MOVIE
            is_movie = 'movie' in detail["title"].lower()
            if not is_movie:
                self.extract_batch_downloads_improved(soup, detail)
            
            # EKSTRAKSI SINGLE EPISODES
            single_episodes_table = soup.find("table", class_="satuk")
            if single_episodes_table:
                for row in single_episodes_table.find_all("tr")[1:]:
                    cells = row.find_all("td")
                    if len(cells) >= 2:
                        episode_cell = cells[0]
                        download_cell = cells[1]
                        
                        episode_name = episode_cell.get_text(strip=True)
                        download_link = download_cell.find("a")
                        
                        if download_link and download_link.get("href") and download_link["href"] != "none":
                            detail["single_episodes"].append({
                                "episode": episode_name,
                                "url": download_link["href"],
                                "provider": "M4U"
                            })
            
            return detail
        except Exception as e:
            print(f"Error in get_anime_detail: {e}")
            return {}

    def extract_streaming_servers(self, soup, detail):
        """Extract streaming servers dengan support multiple quality"""
        episode_servers = []
        
        # METHOD 0: Tipe [Streaming] — iframe tontonin + allvideo episode list
        tontonin = soup.find("iframe", id="tontonin")
        allvideo_links = soup.find_all("a", id="allvideo")
        
        if tontonin or allvideo_links:
            # Kumpulkan semua episode dari data-video
            episodes = []
            for link in allvideo_links:
                if link.get("data-video"):
                    ep_label = link.get_text(strip=True) or "Episode"
                    video_url = self.resolve_url(link["data-video"])
                    episodes.append({
                        "title": ep_label,
                        "url": video_url,
                        "server": "Streaming",
                        "quality": ep_label
                    })
            
            # Kalau ada iframe tapi tidak ada episode list, pakai iframe langsung
            if not episodes and tontonin and tontonin.get("src"):
                episodes.append({
                    "title": "Play",
                    "url": self.resolve_url(tontonin["src"]),
                    "server": "Streaming",
                    "quality": "Default"
                })
            
            if episodes:
                episode_servers.append({
                    "server": "Streaming",
                    "episodes": episodes
                })
            detail["episode_servers"] = episode_servers
            return

        # METHOD 1: Extract dari struktur mirror/vmiror
        mirror_divs = soup.find_all("div", class_=["vmiror", "miror"])
        
        for mirror_div in mirror_divs:
            server_text = mirror_div.get_text(strip=True)
            server_name = "Unknown"
            
            # Deteksi nama server dari text
            if 'btube' in server_text.lower() or 'b-tube' in server_text.lower():
                server_name = "B-Tube"
            elif 'yup' in server_text.lower():
                server_name = "YUp"
            elif 'zippyshare' in server_text.lower():
                server_name = "Zippyshare"
            elif 'racaty' in server_text.lower():
                server_name = "Racaty"
            
            episodes = []
            quality_links = mirror_div.find_all("a", id="allmiror")
            
            for link in quality_links:
                if link.get("data-video"):
                    quality_text = link.get_text(strip=True)
                    video_url = self.resolve_url(link["data-video"])
                    
                    episode_data = {
                        "title": f"{server_name} - {quality_text}",
                        "url": video_url,
                        "server": server_name,
                        "quality": quality_text
                    }
                    episodes.append(episode_data)
            
            if episodes:
                episode_servers.append({
                    "server": server_name,
                    "episodes": episodes
                })
        
        # METHOD 2: Extract dari iframe utama sebagai fallback
        if not episode_servers:
            iframe = soup.find("iframe", id="mediaplayer")
            if iframe and iframe.get("src"):
                episode_servers.append({
                    "server": "B-Tube",
                    "episodes": [{
                        "title": "B-Tube - Default Quality",
                        "url": self.resolve_url(iframe["src"]),
                        "server": "B-Tube",
                        "quality": "360p-720p"
                    }]
                })
        
        detail["episode_servers"] = episode_servers

    def clean_movie_season_description(self, text, title):
        """Bersihkan deskripsi khusus untuk movie dan season - HAPUS UPLOAD INFO"""
        # Bersihkan karakter HTML entities
        clean_text = re.sub(r'&#8220;|&#8221;|&#8230;|&#8217;|&#8220;|&#8221;', '', text)
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        # HAPUS TEXT UPLOAD INFO YANG UMUN DI MOVIE DAN SEASON
        upload_patterns = [
            r'.*?Di unggah oleh.*?anoBoy.*?',
            r'.*?Terbit\s*:\s*[^|]+\|\s*\d+:\d+\s*Wib.*?',
            r'.*?Subtitle Indonesia.*?',
            r'.*?Sub indo.*?',
            r'.*?Selamat menyaksikan\..*?',
            rf'{re.escape(title)}.*?Subtitle Indonesia'
        ]
        
        for pattern in upload_patterns:
            clean_text = re.sub(pattern, '', clean_text, flags=re.IGNORECASE)
        
        # Hapus text yang hanya berisi judul dobel
        if clean_text.strip() == title or len(clean_text.strip()) < 50:
            return None
        
        # Hapus whitespace berlebihan setelah cleaning
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        # Return hanya jika masih ada text yang meaningful
        if len(clean_text) > 50 and not any(keyword in clean_text.lower() for keyword in ['di unggah', 'terbit', 'wib']):
            return clean_text
        
        return None

    def extract_batch_downloads_improved(self, soup, detail):
        """Improved batch download extraction - HANYA UNTUK SERIES, BUKAN MOVIE"""
        provider_links = {}
        
        # METHOD 1: Cari dari div unduhan dengan text batch
        unduhan_divs = soup.find_all("div", class_="unduhan")
        for unduhan in unduhan_divs:
            unduhan_text = unduhan.get_text(strip=True).lower()
            batch_keywords = ['batch', 'download seluruh episode', 'paket', 'repack', 'zip', 'rar', 'full episode']
            
            if any(keyword in unduhan_text for keyword in batch_keywords):
                # Ekstrak links dari unduhan div ini
                self.extract_links_from_container(unduhan, provider_links, "batch")
        
        # METHOD 2: Cari dari hq div dengan text batch
        hq_divs = soup.find_all("div", class_="hq")
        for hq_div in hq_divs:
            hq_text = hq_div.get_text(strip=True).lower()
            if any(keyword in hq_text for keyword in ['batch', 'paket']):
                # Cari div unduhan setelah hq div
                next_elem = hq_div.find_next_sibling()
                while next_elem:
                    if next_elem.name == 'div' and 'unduhan' in next_elem.get('class', []):
                        self.extract_links_from_container(next_elem, provider_links, "batch")
                        break
                    next_elem = next_elem.find_next_sibling()
        
        # METHOD 3: Cari semua span ud yang terkait batch
        all_ud_spans = soup.find_all("span", class_="ud")
        for span in all_ud_spans:
            # Cek context sekitar span untuk deteksi batch
            parent_text = span.parent.get_text(strip=True).lower() if span.parent else ""
            previous_text = ""
            previous_elem = span.find_previous_sibling()
            if previous_elem:
                previous_text = previous_elem.get_text(strip=True).lower()
            
            if any(keyword in parent_text + previous_text for keyword in ['batch', 'paket', 'full episode']):
                self.extract_links_from_span(span, provider_links, "batch")

        # Convert provider_links ke format yang diinginkan
        for provider_name, links in provider_links.items():
            detail["batch_downloads"].append({
                "provider": provider_name,
                "links": links,
                "type": "batch"
            })

    def extract_seasons(self, soup, detail):
        """Extract season structure - FIXED UNTUK MOVIE DAN BATCH"""
        seasons = []
        
        # METHOD 1: Cari dari hq div (untuk series)
        hq_divs = soup.find_all("div", class_="hq")
        for hq_div in hq_divs:
            hq_text = hq_div.get_text(strip=True).lower()
            if 'season' in hq_text or 'episode' in hq_text:
                season_data = {
                    "name": hq_div.get_text(strip=True),
                    "episodes": []
                }
                
                next_div = hq_div.find_next_sibling("div", class_="singlelink")
                if next_div:
                    ul = next_div.find("ul", class_="lcp_catlist")
                    if ul:
                        for li in ul.find_all("li"):
                            link = li.find("a")
                            if link and link.get("href"):
                                season_data["episodes"].append({
                                    "title": self.clean_title(link.get_text(strip=True)),
                                    "url": link["href"]
                                })
                
                if season_data["episodes"]:
                    seasons.append(season_data)
        
        # METHOD 2: Cari dari singlelink langsung (untuk movie yang punya related episodes)
        if not seasons:
            singlelink_div = soup.find("div", class_="singlelink")
            if singlelink_div:
                ul = singlelink_div.find("ul", class_="lcp_catlist")
                if ul:
                    season_data = {
                        "name": "Related Episodes",
                        "episodes": []
                    }
                    
                    for li in ul.find_all("li"):
                        link = li.find("a")
                        if link and link.get("href"):
                            season_data["episodes"].append({
                                "title": self.clean_title(link.get_text(strip=True)),
                                "url": link["href"]
                            })
                    
                    if season_data["episodes"]:
                        seasons.append(season_data)
        
        detail["seasons"] = seasons

    def extract_links_from_container(self, container, provider_links, link_type):
        """Extract download links from a container element"""
        for span in container.find_all("span", class_="ud"):
            self.extract_links_from_span(span, provider_links, link_type)
        
        for link in container.find_all("a", href=True):
            if (link.get("href") and link["href"] != "none" and 
                not link["href"].startswith("javascript")):
                provider = "Unknown"
                quality = "Batch"
                
                link_text = link.get_text(strip=True)
                url = link["href"]
                
                if 'mega.nz' in url:
                    provider = "Mega"
                elif 'ranoz.gg' in url:
                    provider = "RZ"
                elif 'gofile.io' in url:
                    provider = "Gofile"
                elif 'mir.cr' in url:
                    provider = "Mirror"
                elif 'mp4upload.com' in url:
                    provider = "M4U"
                
                if link_text and link_text not in ['Download', 'none']:
                    quality = link_text
                
                if provider not in provider_links:
                    provider_links[provider] = []
                
                provider_links[provider].append({
                    "quality": quality,
                    "url": url
                })

    def extract_links_from_span(self, span, provider_links, link_type):
        """Extract download links from a span element"""
        provider = span.find("span", class_="udj")
        if provider:
            provider_name = provider.text.strip()
            links = span.find_all("a", class_="udl")
            
            if provider_name not in provider_links:
                provider_links[provider_name] = []
            
            for link in links:
                if link.get("href") and link["href"] != "none" and not link["href"].startswith("javascript"):
                    quality = link.text.strip()
                    provider_links[provider_name].append({
                        "quality": quality,
                        "url": link["href"]
                    })

# Initialize scraper
scraper = AnimeScraper()

@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    anime_list = scraper.get_anime_list(page)
    featured_movies = scraper.get_home_movies()
    return render_template('index.html', 
                         anime_list=anime_list, 
                         featured_movies=featured_movies,
                         current_page=page)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    
    if query:
        results = scraper.search_anime(query, page)
    else:
        results = []
    
    return render_template('search.html', results=results, query=query, current_page=page)

@app.route('/movies')
def movie_list():
    page = request.args.get('page', 1, type=int)
    movie_list = scraper.get_movie_list(page)
    return render_template('movies.html', movie_list=movie_list, current_page=page)

@app.route('/jadwal')
def jadwal():
    schedule = scraper.get_schedule()
    return render_template('jadwal.html', schedule=schedule)

@app.route('/anime/<path:anime_path>')
def anime_detail_clean(anime_path):
    """Route bersih untuk detail anime"""
    full_url = f"https://ww1.anoboy.boo/{anime_path}"
    detail = scraper.get_anime_detail(full_url)

    # Skip prev/next untuk movie — cek dari judul aja
    title = detail.get('title', '').lower()
    is_movie = 'movie' in title or ' film' in title
    
    prev_episode = None
    next_episode = None
    if not is_movie:
        prev_next = scraper.get_prev_next_episodes(full_url)
        prev_episode = prev_next["prev"]
        next_episode = prev_next["next"]
    
    return render_template('detail.html', 
                         anime=detail, 
                         clean_url=f"/{anime_path}",
                         prev_episode=prev_episode,
                         next_episode=next_episode)

@app.route('/anime/detail')
def anime_detail_legacy():
    """Route legacy untuk kompatibilitas"""
    anime_url = request.args.get('url', '')
    if anime_url:
        parsed_url = urlparse(anime_url)
        clean_path = parsed_url.path.lstrip('/')
        return redirect(url_for('anime_detail_clean', anime_path=clean_path))
    return "URL anime tidak ditemukan", 404

GENRE_LIST = [
    ("ongoing",        "Ongoing"),
    ("action",         "Action"),
    ("adventure",      "Adventure"),
    ("comedy",         "Comedy"),
    ("demons",         "Demons"),
    ("drama",          "Drama"),
    ("ecchi",          "Ecchi"),
    ("fantasy",        "Fantasy"),
    ("game",           "Game"),
    ("harem",          "Harem"),
    ("historical",     "Historical"),
    ("horror",         "Horror"),
    ("magic",          "Magic"),
    ("martial-arts",   "Martial Arts"),
    ("mecha",          "Mecha"),
    ("military",       "Military"),
    ("music",          "Music"),
    ("mystery",        "Mystery"),
    ("parody",         "Parody"),
    ("police",         "Police"),
    ("psychological",  "Psychological"),
    ("romance",        "Romance"),
    ("samurai",        "Samurai"),
    ("school",         "School"),
    ("shoujo",         "Shoujo"),
    ("shounen",        "Shounen"),
    ("super-power",    "Super Power"),
    ("slice-of-life",  "Slice of Life"),
    ("sci-Fi",         "Sci-Fi"),
    ("seinen",         "Seinen"),
    ("space",          "Space"),
    ("sports",         "Sports"),
    ("Supernatural",   "Supernatural"),
    ("thriller",       "Thriller"),
    ("tokusatsu",      "Tokusatsu"),
    ("vampire",        "Vampire"),
    ("donghua",        "Donghua"),
    ("live-action-movie", "Live Action"),
    ("rekomended",     "Rekomendasi"),
]

@app.route('/genre/<slug>')
def genre_page(slug):
    page = request.args.get('page', 1, type=int)
    # Cari label dari GENRE_LIST
    label = next((name for s, name in GENRE_LIST if s == slug), slug.replace('-', ' ').title())
    items = scraper.get_category_list(slug, page)
    return render_template('genre.html',
                           items=items,
                           slug=slug,
                           label=label,
                           current_page=page,
                           genre_list=GENRE_LIST)

@app.route('/live-action')
def live_action():
    page = request.args.get('page', 1, type=int)
    items = scraper.get_category_list('live-action-movie', page)
    return render_template('genre.html',
                           items=items,
                           slug='live-action-movie',
                           label='Live Action',
                           current_page=page,
                           genre_list=GENRE_LIST)

if __name__ == '__main__':  
    app.run(debug=True, host='0.0.0.0', port=5000)