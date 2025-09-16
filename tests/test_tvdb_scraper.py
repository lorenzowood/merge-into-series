"""Tests for TVDB scraper."""

import pytest
from unittest.mock import Mock, patch

from merge_into_series.tvdb_scraper import TVDBScraper, Episode


def test_episode_creation():
    """Test Episode class functionality."""
    episode = Episode(
        season=2024,
        episode=6,
        title="Praying for Armageddon",
        air_date="May 14, 2024",
        description="A Storyville documentary..."
    )

    assert episode.season == 2024
    assert episode.episode == 6
    assert episode.title == "Praying for Armageddon"
    assert episode.season_episode_code == "S2024E06"


def test_episode_representation():
    """Test Episode string representation."""
    episode = Episode(1, 5, "Test Episode")
    assert "S01E05" in repr(episode)
    assert "Test Episode" in repr(episode)


@patch('merge_into_series.tvdb_scraper.requests.Session.get')
def test_scraper_success(mock_get):
    """Test successful TVDB scraping."""
    # Mock HTML response
    mock_response = Mock()
    mock_response.content = b'''
    <html>
        <li class="list-group-item">
            <h4 class="list-group-item-heading">
                <span class="text-muted episode-label">S2024E06</span>
                <a href="/series/storyville/episodes/10479721">
                    Praying for Armageddon
                </a>
            </h4>
            <ul class="list-inline text-muted">
                <li>May 14, 2024</li>
                <li>BBC Four</li>
            </ul>
            <div class="list-group-item-text">
                <p>A Storyville documentary that explores...</p>
            </div>
        </li>
        <li class="list-group-item">
            <h4 class="list-group-item-heading">
                <span class="text-muted episode-label">S2025E11</span>
                <a href="/series/storyville/episodes/10479722">
                    The Contestant
                </a>
            </h4>
        </li>
    </html>
    '''
    mock_get.return_value = mock_response

    scraper = TVDBScraper()
    episodes = scraper.scrape_episodes('http://example.com')

    assert len(episodes) == 2

    # Check first episode
    ep1 = episodes[0]
    assert ep1.season == 2024
    assert ep1.episode == 6
    assert ep1.title == "Praying for Armageddon"
    assert ep1.air_date == "May 14, 2024"
    assert ep1.episode_id == "10479721"

    # Check second episode
    ep2 = episodes[1]
    assert ep2.season == 2025
    assert ep2.episode == 11
    assert ep2.title == "The Contestant"


def test_scraper_network_error():
    """Test handling of network errors."""
    # Test that network errors are handled gracefully by mocking at instance level
    scraper = TVDBScraper()

    # Create a mock session that raises an exception
    with patch.object(scraper.session, 'get', side_effect=Exception("Network error")):
        episodes = scraper.scrape_episodes('http://example.com')

    assert episodes == []


@patch('merge_into_series.tvdb_scraper.requests.Session.get')
def test_scraper_malformed_html(mock_get):
    """Test handling of malformed HTML."""
    mock_response = Mock()
    mock_response.content = b'''
    <html>
        <li class="list-group-item">
            <!-- Missing episode label -->
            <a href="/series/test/episodes/123">Test Episode</a>
        </li>
        <li class="list-group-item">
            <span class="episode-label">INVALID</span>
            <a href="/series/test/episodes/124">Another Episode</a>
        </li>
    </html>
    '''
    mock_get.return_value = mock_response

    scraper = TVDBScraper()
    episodes = scraper.scrape_episodes('http://example.com')

    # Should handle malformed entries gracefully
    assert episodes == []