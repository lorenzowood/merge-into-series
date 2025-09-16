"""TVDB web scraper for episode data."""

import re
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup


class Episode:
    """Represents a TV episode from TVDB."""

    def __init__(self, season: int, episode: int, title: str, air_date: str = "",
                 description: str = "", episode_id: str = ""):
        self.season = season
        self.episode = episode
        self.title = title
        self.air_date = air_date
        self.description = description
        self.episode_id = episode_id

    def __repr__(self):
        return f"Episode(S{self.season:02d}E{self.episode:02d}, '{self.title}')"

    @property
    def season_episode_code(self) -> str:
        """Return formatted season/episode code like S01E05."""
        return f"S{self.season:04d}E{self.episode:02d}"


class TVDBScraper:
    """Scrape episode information from TVDB pages."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def scrape_episodes(self, tvdb_url: str) -> List[Episode]:
        """Scrape all episodes from a TVDB series page."""
        try:
            response = self.session.get(tvdb_url, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Error fetching TVDB page: {e}")
            return []

        soup = BeautifulSoup(response.content, 'html.parser')
        episodes = []

        # Find all episode list items
        episode_items = soup.find_all('li', class_='list-group-item')

        for item in episode_items:
            try:
                episode = self._parse_episode_item(item)
                if episode:
                    episodes.append(episode)
            except Exception as e:
                print(f"Error parsing episode item: {e}")
                continue

        return episodes

    def _parse_episode_item(self, item) -> Optional[Episode]:
        """Parse a single episode list item."""
        # Look for the episode label (e.g., "S2024E06")
        episode_label = item.find('span', class_='episode-label')
        if not episode_label:
            return None

        # Extract season and episode numbers
        label_text = episode_label.get_text(strip=True)
        match = re.match(r'S(\d+)E(\d+)', label_text)
        if not match:
            return None

        season = int(match.group(1))
        episode_num = int(match.group(2))

        # Extract title
        title_link = item.find('a')
        if not title_link:
            return None

        title = title_link.get_text(strip=True)

        # Extract air date (optional)
        air_date = ""
        date_items = item.find_all('li')
        if date_items:
            air_date = date_items[0].get_text(strip=True)

        # Extract description (optional)
        description = ""
        desc_p = item.find('p')
        if desc_p:
            description = desc_p.get_text(strip=True)

        # Extract episode ID from link
        episode_id = ""
        href = title_link.get('href', '')
        episode_id_match = re.search(r'/episodes/(\d+)', href)
        if episode_id_match:
            episode_id = episode_id_match.group(1)

        return Episode(
            season=season,
            episode=episode_num,
            title=title,
            air_date=air_date,
            description=description,
            episode_id=episode_id
        )