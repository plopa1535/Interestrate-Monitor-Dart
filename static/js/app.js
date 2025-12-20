/**
 * Interest Rate Monitor - Main Application Module
 * Handles AI analysis and news feed functionality
 */

const App = (function() {
    'use strict';

    // Configuration
    const CONFIG = {
        analysisRefreshInterval: 6 * 60 * 60 * 1000, // 6 hours
        newsRefreshInterval: 30 * 60 * 1000, // 30 minutes
        retryDelay: 3000
    };

    // State
    let analysisTimer = null;
    let newsTimer = null;

    /**
     * Initialize the application
     */
    function init() {
        loadAnalysis();
        loadNews();
        setupEventListeners();
        startAutoRefresh();
    }

    /**
     * Setup event listeners
     */
    function setupEventListeners() {
        // Refresh analysis button
        const refreshBtn = document.getElementById('refreshAnalysis');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', function() {
                this.classList.add('loading');
                loadAnalysis().finally(() => {
                    this.classList.remove('loading');
                });
            });
        }
    }

    /**
     * Start auto-refresh timers
     */
    function startAutoRefresh() {
        // Analysis refresh
        analysisTimer = setInterval(loadAnalysis, CONFIG.analysisRefreshInterval);
        
        // News refresh
        newsTimer = setInterval(loadNews, CONFIG.newsRefreshInterval);
    }

    /* =====================
       AI Analysis Module
       ===================== */

    /**
     * Load AI analysis
     */
    async function loadAnalysis() {
        const contentEl = document.getElementById('analysisContent');
        const timeEl = document.getElementById('analysisTime');

        // Show loading state
        if (contentEl) {
            contentEl.innerHTML = `
                <div class="analysis-skeleton">
                    <div class="skeleton-line"></div>
                    <div class="skeleton-line short"></div>
                </div>
            `;
        }

        try {
            const response = await fetch('/api/v1/analysis');
            const result = await response.json();

            if (result.status === 'success' && result.data) {
                // Display analysis
                if (contentEl) {
                    contentEl.textContent = result.data.analysis;
                    contentEl.classList.remove('error');
                }

                // Display generation time
                if (timeEl) {
                    const genTime = new Date(result.data.generated_at);
                    timeEl.textContent = `Generated: ${formatRelativeTime(genTime)}`;
                }
            } else {
                showAnalysisError(contentEl, result.error || 'Failed to load analysis');
            }
        } catch (error) {
            console.error('Error loading analysis:', error);
            showAnalysisError(contentEl, 'Network error');
        }
    }

    /**
     * Show analysis error
     */
    function showAnalysisError(element, message) {
        if (element) {
            element.textContent = '현재 AI 분석을 불러올 수 없습니다. 잠시 후 다시 시도해 주세요.';
            element.classList.add('error');
        }
    }

    /* =====================
       News Feed Module
       ===================== */

    /**
     * Load news feed
     */
    async function loadNews() {
        const usListEl = document.getElementById('usNewsList');
        const krListEl = document.getElementById('krNewsList');

        // Show loading state
        showNewsSkeleton(usListEl);
        showNewsSkeleton(krListEl);

        try {
            const response = await fetch('/api/v1/news?country=all&limit=5');
            const result = await response.json();

            if (result.status === 'success' && result.data) {
                renderNewsColumn(usListEl, result.data.us);
                renderNewsColumn(krListEl, result.data.kr);
            } else {
                showNewsError(usListEl, result.error);
                showNewsError(krListEl, result.error);
            }
        } catch (error) {
            console.error('Error loading news:', error);
            showNewsError(usListEl, 'Network error');
            showNewsError(krListEl, 'Network error');
        }
    }

    /**
     * Show news skeleton loading
     */
    function showNewsSkeleton(element) {
        if (!element) return;
        
        element.innerHTML = `
            <div class="news-skeleton">
                <div class="skeleton-card"></div>
                <div class="skeleton-card"></div>
                <div class="skeleton-card"></div>
            </div>
        `;
    }

    /**
     * Render news column
     */
    function renderNewsColumn(element, newsItems) {
        if (!element) return;

        if (!newsItems || newsItems.length === 0) {
            element.innerHTML = `
                <div class="news-empty">
                    <p>최신 뉴스가 없습니다.</p>
                </div>
            `;
            return;
        }

        const html = newsItems.map(item => createNewsCard(item)).join('');
        element.innerHTML = html;
    }

    /**
     * Create news card HTML
     */
    function createNewsCard(item) {
        const title = escapeHtml(item.title || 'No title');
        const source = escapeHtml(item.source || 'Unknown');
        const snippet = escapeHtml(item.snippet || '');
        const relativeTime = item.relative_time || '';
        const url = item.url || '#';

        return `
            <a href="${url}" class="news-card" target="_blank" rel="noopener noreferrer">
                <h4 class="news-title">${title}</h4>
                <div class="news-meta">
                    <span class="news-source">${source}</span>
                    <span class="news-time">${relativeTime}</span>
                </div>
                ${snippet ? `<p class="news-snippet">${snippet}</p>` : ''}
            </a>
        `;
    }

    /**
     * Show news error
     */
    function showNewsError(element, message) {
        if (!element) return;
        
        element.innerHTML = `
            <div class="news-empty">
                <p>뉴스를 불러올 수 없습니다.</p>
                <button onclick="App.loadNews()" style="
                    margin-top: 10px;
                    padding: 8px 16px;
                    background: var(--google-blue);
                    color: white;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                ">다시 시도</button>
            </div>
        `;
    }

    /* =====================
       Utility Functions
       ===================== */

    /**
     * Format relative time
     */
    function formatRelativeTime(date) {
        const now = new Date();
        const diff = now - date;
        
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);

        if (days > 0) {
            return `${days}일 전`;
        } else if (hours > 0) {
            return `${hours}시간 전`;
        } else if (minutes > 0) {
            return `${minutes}분 전`;
        } else {
            return '방금 전';
        }
    }

    /**
     * Escape HTML special characters
     */
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Cleanup timers
     */
    function destroy() {
        if (analysisTimer) {
            clearInterval(analysisTimer);
        }
        if (newsTimer) {
            clearInterval(newsTimer);
        }
    }

    // Public API
    return {
        init: init,
        loadAnalysis: loadAnalysis,
        loadNews: loadNews,
        destroy: destroy
    };
})();

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    App.init();
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    App.destroy();
});
