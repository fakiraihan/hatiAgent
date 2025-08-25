// Hati Chat Interface JavaScript with Memory & Personalization

class HatiChat {
    constructor() {
        this.backendUrl = 'api.php'; // Use PHP proxy instead of direct backend
        this.userId = this.getOrCreateUserId();
        this.sessionId = this.getOrCreateSessionId();
        this.userProfile = this.loadUserProfile();
        this.isConnected = false;
        this.conversationHistory = [];
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.checkConnection();
        this.loadSettings();
        this.restoreConversationHistory();
        this.displayWelcomeMessage();
    }

    getOrCreateUserId() {
        let userId = localStorage.getItem('hati_user_id');
        if (!userId) {
            userId = 'user_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('hati_user_id', userId);
        }
        return userId;
    }

    getOrCreateSessionId() {
        let sessionId = sessionStorage.getItem('hati_session_id');
        if (!sessionId) {
            sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            sessionStorage.setItem('hati_session_id', sessionId);
        }
        return sessionId;
    }

    loadUserProfile() {
        const profile = localStorage.getItem('hati_user_profile');
        return profile ? JSON.parse(profile) : {
            name: null,
            preferredGenres: [],
            moodHistory: [],
            preferences: {}
        };
    }

    saveUserProfile() {
        localStorage.setItem('hati_user_profile', JSON.stringify(this.userProfile));
    }

    restoreConversationHistory() {
        const history = sessionStorage.getItem('hati_conversation');
        if (history) {
            this.conversationHistory = JSON.parse(history);
            // Restore messages to UI
            this.conversationHistory.forEach(msg => {
                if (msg.type === 'user') {
                    this.displayUserMessage(msg.content, false);
                } else {
                    this.displayBotMessage(msg.content, msg.data || {}, false);
                }
            });
        }
    }

    saveConversationHistory() {
        sessionStorage.setItem('hati_conversation', JSON.stringify(this.conversationHistory));
    }

    displayWelcomeMessage() {
        if (this.conversationHistory.length === 0) {
            const welcomeMsg = this.userProfile.name 
                ? `Selamat datang kembali, ${this.userProfile.name}! 🌟 Bagaimana perasaanmu hari ini?`
                : 'Halo! Saya Hati, asisten AI untuk membantu mengelola suasana hatimu. 💙 Ceritakan bagaimana perasaanmu hari ini?';
                
            this.displayBotMessage(welcomeMsg, {}, false);
            this.addToHistory('bot', welcomeMsg);
        }
    }

    setupEventListeners() {
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendButton');

        // Enable/disable send button based on input
        messageInput.addEventListener('input', () => {
            const hasContent = messageInput.value.trim().length > 0;
            sendButton.disabled = !hasContent;
        });

        // Auto-resize textarea
        messageInput.addEventListener('input', () => {
            this.autoResize(messageInput);
        });
    }

    autoResize(textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }

    async checkConnection() {
        try {
            const response = await fetch(`${this.backendUrl}/health`);
            if (response.ok) {
                this.setConnectionStatus(true);
            } else {
                this.setConnectionStatus(false);
            }
        } catch (error) {
            console.error('Connection check failed:', error);
            this.setConnectionStatus(false);
        }
    }

    setConnectionStatus(connected) {
        this.isConnected = connected;
        const statusElement = document.getElementById('connectionStatus');
        if (connected) {
            statusElement.textContent = 'Terhubung';
            statusElement.style.color = '#4AE54A';
        } else {
            statusElement.textContent = 'Tidak Terhubung';
            statusElement.style.color = '#FF6B6B';
        }
    }

    async sendMessage(message = null) {
        const messageInput = document.getElementById('messageInput');
        const messageText = message || messageInput.value.trim();

        if (!messageText) return;

        // Clear input if not from quick action
        if (!message) {
            messageInput.value = '';
            messageInput.style.height = 'auto';
            document.getElementById('sendButton').disabled = true;
        }

        // Add user message to chat and history
        this.displayUserMessage(messageText);
        this.addToHistory('user', messageText);

        // Show typing indicator
        this.showTypingIndicator();

        try {
            const response = await fetch(`${this.backendUrl}/chat-enhanced`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: messageText,
                    user_id: this.userId,
                    session_id: this.sessionId,
                    user_name: this.userProfile.name,
                    preferences: this.userProfile.preferences
                })
            });

            this.hideTypingIndicator();

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            // Update session ID if it was auto-generated
            if (data.session_id && data.session_id !== this.sessionId) {
                this.sessionId = data.session_id;
                sessionStorage.setItem('hati_session_id', this.sessionId);
            }
            
            // Learn from the interaction
            this.learnFromInteraction(messageText, data);
            
            console.log('=== FRONTEND DEBUG ===');
            console.log('Full response data:', data);
            console.log('Agent used:', data.agent_used);
            console.log('Specialist data:', data.specialist_data);
            console.log('Personalized:', data.personalized);
            console.log('=== END DEBUG ===');
            
            this.displayBotMessage(data.response, data, true);
            this.addToHistory('bot', data.response, data.specialist_data);

            // Log performance info if debug mode is enabled
            console.log('Response time:', data.processing_time + 's');
            console.log('Agent used:', data.agent_used);
            console.log('Mood detected:', data.mood_detected);
            console.log('Specialist data:', data.specialist_data);
            
            // Debug relaxation data structure
            if (data.agent_used === 'relaxation') {
                console.log('Relaxation places:', data.specialist_data.activities?.places);
                console.log('All activities:', data.specialist_data.activities);
            }
            
            // Debug entertainment data structure
            if (data.agent_used === 'entertainment') {
                console.log('Entertainment content:', data.specialist_data.content);
                console.log('Movies:', data.specialist_data.content?.movies);
                console.log('GIFs:', data.specialist_data.content?.gifs);
            }

        } catch (error) {
            this.hideTypingIndicator();
            console.error('Error sending message:', error);
            
            let errorMessage = 'Maaf, aku sedang mengalami masalah teknis. ';
            if (!this.isConnected) {
                errorMessage += 'Sepertinya koneksi ke server terputus. Coba periksa pengaturan atau coba lagi nanti.';
            } else {
                errorMessage += 'Coba kirim pesan lagi dalam beberapa saat.';
            }
            
            this.addMessage(errorMessage, 'bot', true);
        }
    }

    addMessage(text, sender, isError = false) {
        const chatMessages = document.getElementById('chatMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        if (isError) {
            messageDiv.classList.add('error-message');
        }

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        
        if (sender === 'bot') {
            avatar.innerHTML = '<i class="fas fa-heart"></i>';
        } else {
            avatar.innerHTML = '<i class="fas fa-user"></i>';
        }

        const content = document.createElement('div');
        content.className = 'message-content';
        
        const messageText = document.createElement('div');
        
        // Process text to convert Spotify links
        const processedText = this.processSpotifyLinks(text);
        messageText.innerHTML = processedText;
        
        const timestamp = document.createElement('div');
        timestamp.className = 'message-time';
        timestamp.textContent = new Date().toLocaleTimeString('id-ID', {
            hour: '2-digit',
            minute: '2-digit'
        });

        content.appendChild(messageText);
        content.appendChild(timestamp);
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(content);

        chatMessages.appendChild(messageDiv);
        
        // Scroll to bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Memory and learning methods
    addToHistory(type, content, data = null) {
        this.conversationHistory.push({
            type: type,
            content: content,
            data: data,
            timestamp: Date.now()
        });
        
        // Keep only last 50 messages to avoid memory issues
        if (this.conversationHistory.length > 50) {
            this.conversationHistory = this.conversationHistory.slice(-50);
        }
        
        this.saveConversationHistory();
    }

    learnFromInteraction(userMessage, responseData) {
        try {
            // Learn mood patterns
            if (responseData.mood_detected) {
                if (!this.userProfile.moodHistory) {
                    this.userProfile.moodHistory = [];
                }
                
                this.userProfile.moodHistory.push({
                    mood: responseData.mood_detected,
                    timestamp: Date.now(),
                    trigger: userMessage.substring(0, 100) // First 100 chars as trigger
                });
                
                // Keep only last 30 mood entries
                if (this.userProfile.moodHistory.length > 30) {
                    this.userProfile.moodHistory = this.userProfile.moodHistory.slice(-30);
                }
            }
            
            // Learn music preferences
            if (responseData.agent_used === 'music' && responseData.specialist_data) {
                const genre = responseData.specialist_data.genre;
                if (genre && !this.userProfile.preferredGenres.includes(genre)) {
                    this.userProfile.preferredGenres.push(genre);
                }
            }
            
            // Update general preferences
            if (!this.userProfile.preferences) {
                this.userProfile.preferences = {};
            }
            
            this.userProfile.preferences.lastAgent = responseData.agent_used;
            this.userProfile.preferences.lastMood = responseData.mood_detected;
            
            this.saveUserProfile();
            
        } catch (error) {
            console.warn('Failed to learn from interaction:', error);
        }
    }

    displayUserMessage(text, addToHistory = true) {
        this.addMessage(text, 'user');
    }

    displayBotMessage(text, data = {}, addToHistory = true) {
        this.addEnhancedMessage(text, data.specialist_data || data, data.agent_used || 'bot', data.mood_detected, data.processing_time);
    }

    async provideFeedback(agentType, trackId, feedback, data = {}) {
        try {
            await fetch(`${this.backendUrl}/feedback/${this.sessionId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    agent_type: agentType,
                    track_id: trackId,
                    feedback: feedback,
                    data: data
                })
            });
        } catch (error) {
            console.warn('Failed to send feedback:', error);
        }
    }

    addEnhancedMessage(text, specialistData, agentUsed, moodDetected, processingTime) {
        console.log('=== addEnhancedMessage called ===');
        console.log('Text:', text);
        console.log('Agent used:', agentUsed);
        console.log('Specialist data:', specialistData);
        console.log('================================');
        
        const chatMessages = document.getElementById('chatMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot-message enhanced-message';

        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.innerHTML = '<i class="fas fa-heart"></i>';

        const content = document.createElement('div');
        content.className = 'message-content';
        
        const messageText = document.createElement('div');
        messageText.className = 'main-response';
        
        // For music responses, remove Spotify links from text and show as cards instead
        console.log('=== PROCESSING AGENT TYPE ===');
        console.log('Agent used:', agentUsed);
        console.log('Type of agentUsed:', typeof agentUsed);
        console.log('Is entertainment?', agentUsed === 'entertainment');
        console.log('Specialist data exists?', !!specialistData);
        console.log('Has content?', !!specialistData?.content);
        console.log('================================');
        
        if (agentUsed === 'music' && specialistData && specialistData.recommendations) {
            // Remove all Spotify links from the text
            let cleanedText = text.replace(/🎵 \[([^\]]+)\]\((https:\/\/open\.spotify\.com\/track\/[^)]+)\)/g, '');
            // Clean up any remaining text about clicking links
            cleanedText = cleanedText.replace(/Silakan klik link di atas untuk mendengarkan langsung di Spotify!.*$/gi, '');
            cleanedText = cleanedText.trim();
            
            messageText.innerHTML = cleanedText;
            
            // Add music cards
            const musicCardsHtml = this.createMusicCards(specialistData.recommendations);
            messageText.innerHTML += musicCardsHtml;
        } else if (agentUsed === 'relaxation' && specialistData && 
                   (specialistData.places || (specialistData.activities && specialistData.activities.places))) {
            // For relaxation responses, show place cards instead of long text
            let cleanedText = text;
            // Remove detailed place descriptions and keep only the main message
            cleanedText = cleanedText.replace(/\d+\.\s*\*\*[^*]+\*\*.*?(?=\d+\.\s*\*\*|\s*$)/gs, '');
            cleanedText = cleanedText.replace(/Berikut adalah tempat.*?tenang.*?:/gi, '');
            cleanedText = cleanedText.trim();
            
            // If there's still meaningful text, show it
            if (cleanedText && cleanedText.length > 50) {
                messageText.innerHTML = cleanedText;
            } else {
                messageText.innerHTML = 'Berikut adalah tempat-tempat yang sempurna untuk relaksasi dan ketenangan:';
            }
            
            // Get places from the correct data structure
            const places = specialistData.places || specialistData.activities?.places || [];
            
            // Add place cards
            const placeCardsHtml = this.createPlaceCards(places);
            messageText.innerHTML += placeCardsHtml;
        } else if (agentUsed === 'entertainment') {
            console.log('Entertainment agent detected');
            console.log('Specialist data:', specialistData);
            console.log('Has content?', !!specialistData?.content);
            
            if (specialistData && specialistData.content) {
                // For entertainment responses, show text first
                let cleanedText = text;
                
                console.log('Entertainment processing - specialist data:', specialistData);
                console.log('Entertainment content:', specialistData.content);
                console.log('Movies available:', specialistData.content.movies);
                console.log('GIFs available:', specialistData.content.gifs);
                
                messageText.innerHTML = cleanedText;
                content.appendChild(messageText);
                
                // Add movie cards in separate bubble if available
                if (specialistData.content.movies && specialistData.content.movies.length > 0) {
                    console.log('Creating movie cards for:', specialistData.content.movies);
                    
                    // Create movie bubble with proper content
                    const movieBubble = document.createElement('div');
                    movieBubble.className = 'message-content';
                    
                    const movieHeader = document.createElement('div');
                    movieHeader.className = 'content-header';
                    movieHeader.innerHTML = '<i class="fas fa-film"></i> Movies';
                    movieHeader.style.cssText = 'font-weight: bold; margin-bottom: 10px; color: #667eea;';
                    
                    const movieContent = document.createElement('div');
                    movieContent.className = 'movies-content';
                    movieContent.innerHTML = this.createMovieCards(specialistData.content.movies);
                    
                    movieBubble.appendChild(movieHeader);
                    movieBubble.appendChild(movieContent);
                    
                    // Create separate message for movies
                    const movieMessageDiv = document.createElement('div');
                    movieMessageDiv.className = 'message bot-message enhanced-message';
                    
                    const movieAvatar = document.createElement('div');
                    movieAvatar.className = 'message-avatar';
                    movieAvatar.innerHTML = '<i class="fas fa-film"></i>';
                    
                    movieMessageDiv.appendChild(movieAvatar);
                    movieMessageDiv.appendChild(movieBubble);
                    
                    console.log('Adding movie bubble to chat...');
                    const chatContainer = document.getElementById('chatMessages');
                    if (chatContainer) {
                        chatContainer.appendChild(movieMessageDiv);
                        console.log('Movie bubble added successfully');
                        this.scrollToBottom();
                    } else {
                        console.error('Chat container not found!');
                    }
                }
                
                // Add GIF cards in separate bubble if available  
                if (specialistData.content.gifs && specialistData.content.gifs.length > 0) {
                    console.log('Creating GIF cards for:', specialistData.content.gifs);
                    const gifBubble = this.createSeparateContentBubble('gifs', specialistData.content.gifs);
                    
                    // Create separate message for GIFs
                    const gifMessageDiv = document.createElement('div');
                    gifMessageDiv.className = 'message bot-message enhanced-message';
                    
                    const gifAvatar = document.createElement('div');
                    gifAvatar.className = 'message-avatar';
                    gifAvatar.innerHTML = '<i class="fas fa-images"></i>';
                    
                    gifMessageDiv.appendChild(gifAvatar);
                    gifMessageDiv.appendChild(gifBubble);
                    
                    console.log('GIF message div created:', gifMessageDiv);
                    
                    // Store reference to this for setTimeout
                    const self = this;
                    
                    // Add to chat after movie message (if exists) 
                    const delay = specialistData.content.movies && specialistData.content.movies.length > 0 ? 600 : 300;
                    setTimeout(() => {
                        console.log('Adding GIF bubble to chat...');
                        const chatContainer = document.getElementById('chatMessages');
                        if (chatContainer) {
                            chatContainer.appendChild(gifMessageDiv);
                            console.log('GIF bubble added successfully');
                            self.scrollToBottom();
                        } else {
                            console.error('Chat container not found!');
                        }
                    }, delay);
                }
                
                // Skip the normal content.appendChild(messageText) since we already added it
                return;
            } else {
                console.log('Entertainment agent but no content data');
                let processedText = this.processSpotifyLinks(text);
                messageText.innerHTML = processedText;
            }
        } else {
            // For non-music/non-relaxation responses, process normally
            let processedText = this.processSpotifyLinks(text);
            messageText.innerHTML = processedText;
        }
        
        content.appendChild(messageText);

        // Agent workflow details (collapsible) - similar to Gemini
        const workflowDiv = document.createElement('div');
        workflowDiv.className = 'agent-workflow';
        
        const toggleButton = document.createElement('button');
        toggleButton.className = 'workflow-toggle';
        toggleButton.innerHTML = `
            <i class="fas fa-cog"></i> 
            <span>Lihat cara kerja agent</span>
            <i class="fas fa-chevron-down"></i>
        `;
        
        const workflowDetails = document.createElement('div');
        workflowDetails.className = 'workflow-details';
        workflowDetails.style.display = 'none';
        
        workflowDetails.innerHTML = this.createWorkflowSteps(agentUsed, moodDetected, processingTime, specialistData);
        
        toggleButton.addEventListener('click', () => {
            const isVisible = workflowDetails.style.display !== 'none';
            workflowDetails.style.display = isVisible ? 'none' : 'block';
            const chevron = toggleButton.querySelector('.fa-chevron-down, .fa-chevron-up');
            chevron.className = isVisible ? 'fas fa-chevron-down' : 'fas fa-chevron-up';
            
            // Scroll to show the expanded content
            if (!isVisible) {
                setTimeout(() => {
                    messageDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }, 100);
            }
        });
        
        workflowDiv.appendChild(toggleButton);
        workflowDiv.appendChild(workflowDetails);
        content.appendChild(workflowDiv);
        
        const timestamp = document.createElement('div');
        timestamp.className = 'message-time';
        timestamp.textContent = new Date().toLocaleTimeString('id-ID', {
            hour: '2-digit',
            minute: '2-digit'
        });

        content.appendChild(timestamp);
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(content);

        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    createMusicCards(recommendations) {
        let musicCardsHtml = '<div class="music-cards-container">';
        
        recommendations.forEach(track => {
            const coverUrl = track.cover_url || 'https://via.placeholder.com/80x80/1DB954/FFFFFF?text=🎵';
            
            musicCardsHtml += `
                <div class="music-card-enhanced">
                    <img src="${coverUrl}" alt="${track.album}" class="album-cover" loading="lazy" 
                         onerror="this.src='https://via.placeholder.com/80x80/1DB954/FFFFFF?text=🎵'">
                    <div class="music-info-enhanced">
                        <div class="music-title-enhanced">${track.title}</div>
                        <div class="music-artist-enhanced">${track.artist}</div>
                    </div>
                    <button class="spotify-button-compact" onclick="window.open('${track.url}', '_blank')">
                        <i class="fab fa-spotify"></i>
                        <span>Play</span>
                    </button>
                </div>
            `;
        });
        
        musicCardsHtml += '</div>';
        return musicCardsHtml;
    }

    createPlaceCards(places) {
        let placeCardsHtml = '<div class="place-cards-container">';
        
        places.forEach(place => {
            const placeIcon = this.getPlaceIcon(place.category);
            const rating = place.rating ? `⭐ ${place.rating}` : '';
            const mapsUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(place.name + ' ' + place.address)}`;
            
            placeCardsHtml += `
                <div class="place-card-enhanced">
                    <div class="place-icon">
                        <i class="${placeIcon}"></i>
                    </div>
                    <div class="place-info-enhanced">
                        <div class="place-name-enhanced">${place.name}</div>
                        <div class="place-address-enhanced">${place.address}</div>
                        ${rating ? `<div class="place-rating-enhanced">${rating}</div>` : ''}
                    </div>
                    <button class="maps-button-compact" onclick="window.open('${mapsUrl}', '_blank')">
                        <i class="fas fa-map-marker-alt"></i>
                        <span>Directions</span>
                    </button>
                </div>
            `;
        });
        
        placeCardsHtml += '</div>';
        return placeCardsHtml;
    }

    getPlaceIcon(category) {
        const iconMap = {
            'park': 'fas fa-tree',
            'temple': 'fas fa-place-of-worship',
            'museum': 'fas fa-university',
            'beach': 'fas fa-umbrella-beach',
            'mountain': 'fas fa-mountain',
            'shopping': 'fas fa-shopping-bag',
            'restaurant': 'fas fa-utensils',
            'hotel': 'fas fa-bed',
            'spa': 'fas fa-spa',
            'garden': 'fas fa-seedling',
            'waterfall': 'fas fa-water',
            'lake': 'fas fa-water',
            'default': 'fas fa-map-marker-alt'
        };
        
        return iconMap[category?.toLowerCase()] || iconMap.default;
    }

    createMovieCards(movies) {
        console.log('createMovieCards called with:', movies);
        
        if (!movies || !Array.isArray(movies) || movies.length === 0) {
            console.log('No movies to create cards for');
            return '';
        }
        
        let movieCardsHtml = '<div class="movie-cards-container">';
        
        movies.forEach((movie, index) => {
            console.log(`Processing movie ${index}:`, movie);
            
            const posterUrl = movie.poster_url || 'https://via.placeholder.com/200x300/667eea/FFFFFF?text=🎬';
            const rating = movie.rating ? `⭐ ${movie.rating.toFixed(1)}` : '';
            const year = movie.release_date ? new Date(movie.release_date).getFullYear() : '';
            const shortOverview = movie.overview?.length > 100 ? 
                movie.overview.substring(0, 100) + '...' : movie.overview;
            
            movieCardsHtml += `
                <div class="movie-card-enhanced">
                    <div class="movie-poster">
                        <img src="${posterUrl}" alt="${movie.title}" loading="lazy" 
                             onerror="this.src='https://via.placeholder.com/200x300/667eea/FFFFFF?text=🎬'">
                        <div class="movie-overlay">
                            <div class="movie-rating">${rating}</div>
                            <div class="movie-year">${year}</div>
                        </div>
                    </div>
                    <div class="movie-info">
                        <div class="movie-title">${movie.title}</div>
                        <div class="movie-overview">${shortOverview}</div>
                    </div>
                </div>
            `;
        });
        
        movieCardsHtml += '</div>';
        console.log('Generated movie cards HTML:', movieCardsHtml);
        return movieCardsHtml;
    }

    createGifCards(gifs) {
        console.log('createGifCards called with:', gifs);
        
        if (!gifs || !Array.isArray(gifs) || gifs.length === 0) {
            console.log('No GIFs to create cards for');
            return '';
        }
        
        let gifCardsHtml = '<div class="gif-cards-container">';
        
        gifs.forEach((gif, index) => {
            console.log(`Processing GIF ${index}:`, gif);
            
            const gifUrl = gif.url || gif.images?.fixed_height?.url || '';
            const title = gif.title || 'Mood GIF';
            const rating = gif.rating ? gif.rating.toUpperCase() : 'G';
            
            gifCardsHtml += `
                <div class="gif-card">
                    <div class="gif-container">
                        <img src="${gifUrl}" alt="${title}" loading="lazy" 
                             onerror="this.src='https://via.placeholder.com/200x150/667eea/FFFFFF?text=🎭'">
                        <div class="gif-overlay">
                            <div class="gif-rating">${rating}</div>
                        </div>
                    </div>
                    <div class="gif-info">
                        <div class="gif-title">${title}</div>
                    </div>
                </div>
            `;
        });
        
        gifCardsHtml += '</div>';
        console.log('Generated GIF cards HTML:', gifCardsHtml);
        return gifCardsHtml;
    }

    processSpotifyLinks(text) {
        // Convert markdown-style Spotify links to clickable music cards
        // Pattern: 🎵 [Song Title - Artist](spotify_url)
        const spotifyLinkRegex = /🎵 \[([^\]]+)\]\((https:\/\/open\.spotify\.com\/track\/[^)]+)\)/g;
        
        let processedText = text.replace(spotifyLinkRegex, (match, title, url) => {
            // Extract song and artist from title
            const parts = title.split(' - ');
            const songTitle = parts[0] || title;
            const artist = parts.slice(1).join(' - ') || 'Unknown Artist';
            
            return `<div class="music-card">
                <div class="music-card-content">
                    <div class="music-info">
                        <div class="music-title">${songTitle}</div>
                        <div class="music-artist">${artist}</div>
                    </div>
                    <button class="spotify-button" onclick="window.open('${url}', '_blank')">
                        <i class="fab fa-spotify"></i>
                        <span>Play on Spotify</span>
                        <i class="fas fa-external-link-alt"></i>
                    </button>
                </div>
            </div>`;
        });

        // Convert regular URLs to clickable links
        const urlRegex = /(https?:\/\/[^\s]+)/g;
        processedText = processedText.replace(urlRegex, (url) => {
            if (url.includes('spotify.com')) {
                // Skip if already processed as Spotify link
                return url;
            }
            return `<a href="${url}" target="_blank" rel="noopener noreferrer">${url}</a>`;
        });

        // Convert line breaks to <br>
        processedText = processedText.replace(/\n/g, '<br>');
        
        return processedText;
    }

    createSeparateContentBubble(contentType, content) {
        console.log(`Creating separate ${contentType} bubble for:`, content);
        
        const bubbleDiv = document.createElement('div');
        bubbleDiv.className = 'message-content content-bubble';
        console.log('Created bubbleDiv:', bubbleDiv);
        
        const contentDiv = document.createElement('div');
        contentDiv.className = `${contentType}-content`;
        console.log('Created contentDiv:', contentDiv);
        
        // Add content type header
        const headerDiv = document.createElement('div');
        headerDiv.className = 'content-header';
        
        if (contentType === 'movies') {
            headerDiv.innerHTML = '<i class="fas fa-film"></i> Movies';
            console.log('Setting movies header:', headerDiv.innerHTML);
            const movieCardsHTML = this.createMovieCards(content);
            console.log('Movie cards HTML from createMovieCards:', movieCardsHTML);
            contentDiv.innerHTML = movieCardsHTML;
            console.log('ContentDiv after setting innerHTML:', contentDiv);
        } else if (contentType === 'gifs') {
            headerDiv.innerHTML = '<i class="fas fa-images"></i> GIFs';
            contentDiv.innerHTML = this.createGifCards(content);
        }
        
        console.log('Appending headerDiv to bubbleDiv...');
        bubbleDiv.appendChild(headerDiv);
        console.log('Appending contentDiv to bubbleDiv...');
        bubbleDiv.appendChild(contentDiv);
        
        // Add timestamp
        const timestamp = document.createElement('div');
        timestamp.className = 'message-time';
        timestamp.textContent = new Date().toLocaleTimeString('id-ID', {
            hour: '2-digit',
            minute: '2-digit'
        });
        console.log('Appending timestamp to bubbleDiv...');
        bubbleDiv.appendChild(timestamp);
        
        console.log('Final bubbleDiv:', bubbleDiv);
        console.log('Final bubbleDiv HTML:', bubbleDiv.outerHTML);
        return bubbleDiv;
    }

    showTypingIndicator() {
        const typingIndicator = document.getElementById('typingIndicator');
        typingIndicator.style.display = 'flex';
        
        // Scroll to bottom
        const chatMessages = document.getElementById('chatMessages');
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    hideTypingIndicator() {
        const typingIndicator = document.getElementById('typingIndicator');
        typingIndicator.style.display = 'none';
    }

    sendQuickMessage(message) {
        this.sendMessage(message);
    }

    handleKeyPress(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            this.sendMessage();
        }
    }

    toggleSettings() {
        const settingsPanel = document.getElementById('settingsPanel');
        settingsPanel.classList.toggle('open');
    }

    async testConnection() {
        const loadingOverlay = document.getElementById('loadingOverlay');
        loadingOverlay.style.display = 'flex';

        try {
            const backendUrlInput = document.getElementById('backendUrl');
            const testUrl = backendUrlInput.value || this.backendUrl;
            
            const response = await fetch(`${testUrl}/health`);
            const data = await response.json();
            
            if (response.ok) {
                alert(`✅ Koneksi berhasil!\n\nStatus: ${data.status}\nAgen terdaftar: ${data.agents_registered}\nGroq terhubung: ${data.groq_connected ? 'Ya' : 'Tidak'}`);
                
                // Update backend URL if test successful
                this.backendUrl = testUrl;
                this.setConnectionStatus(true);
                this.saveSettings();
            } else {
                alert('❌ Koneksi gagal: ' + data.detail);
            }
        } catch (error) {
            alert('❌ Error koneksi: ' + error.message);
        } finally {
            loadingOverlay.style.display = 'none';
        }
    }

    isDebugMode() {
        const debugCheckbox = document.getElementById('debugMode');
        return debugCheckbox.checked;
    }

    saveSettings() {
        const settings = {
            backendUrl: document.getElementById('backendUrl').value,
            debugMode: document.getElementById('debugMode').checked,
            userId: this.userId,
            sessionId: this.sessionId
        };
        localStorage.setItem('hatiSettings', JSON.stringify(settings));
    }

    loadSettings() {
        const saved = localStorage.getItem('hatiSettings');
        if (saved) {
            const settings = JSON.parse(saved);
            
            document.getElementById('backendUrl').value = settings.backendUrl || this.backendUrl;
            document.getElementById('debugMode').checked = settings.debugMode || false;
            
            if (settings.backendUrl) {
                this.backendUrl = settings.backendUrl;
            }
            
            if (settings.userId) {
                this.userId = settings.userId;
            }
            
            if (settings.sessionId) {
                this.sessionId = settings.sessionId;
            }
        }
    }

    createWorkflowSteps(agentUsed, moodDetected, processingTime, specialistData) {
        return `
            <div class="workflow-step">
                <div class="step-header">
                    <div class="step-icon"><i class="fas fa-brain"></i></div>
                    <div class="step-info">
                        <div class="step-title">1. Analisis Pesan</div>
                        <div class="step-desc">Groq LLM menganalisis mood dan menentukan agent</div>
                    </div>
                </div>
                <div class="step-content">
                    <div class="step-data">
                        <span class="data-label">Mood terdeteksi:</span> 
                        <span class="data-value mood-${moodDetected}">${moodDetected}</span>
                    </div>
                    <div class="step-data">
                        <span class="data-label">Agent dipilih:</span> 
                        <span class="data-value agent-${agentUsed}">${this.getAgentName(agentUsed)}</span>
                    </div>
                </div>
            </div>
            
            <div class="workflow-step">
                <div class="step-header">
                    <div class="step-icon"><i class="fas fa-robot"></i></div>
                    <div class="step-info">
                        <div class="step-title">2. Eksekusi Specialist</div>
                        <div class="step-desc">${this.getAgentDescription(agentUsed)}</div>
                    </div>
                </div>
                <div class="step-content">
                    ${this.formatSpecialistData(agentUsed, specialistData)}
                </div>
            </div>
            
            <div class="workflow-step">
                <div class="step-header">
                    <div class="step-icon"><i class="fas fa-comment-dots"></i></div>
                    <div class="step-info">
                        <div class="step-title">3. Personalisasi Respons</div>
                        <div class="step-desc">Groq LLM mengubah data teknis menjadi percakapan natural</div>
                    </div>
                </div>
                <div class="step-content">
                    <div class="step-data">
                        <span class="data-label">Waktu proses:</span> 
                        <span class="data-value">${processingTime?.toFixed(2) || 'N/A'}s</span>
                    </div>
                    <div class="step-data">
                        <span class="data-label">Model:</span> 
                        <span class="data-value">Groq LLaMA 3 70B</span>
                    </div>
                </div>
            </div>
        `;
    }

    getAgentName(agentUsed) {
        const names = {
            'music': '🎵 Music Agent',
            'entertainment': '🎭 Entertainment Agent', 
            'relaxation': '🧘 Relaxation Agent',
            'reflection': '💭 Reflection Agent'
        };
        return names[agentUsed] || agentUsed;
    }

    getAgentDescription(agentUsed) {
        const descriptions = {
            'music': 'Mencari musik di Spotify berdasarkan mood',
            'entertainment': 'Mencari konten hiburan via Giphy & TMDb API',
            'relaxation': 'Menyediakan tips relaksasi dan tempat tenang',
            'reflection': 'Memberikan dukungan emosional dan refleksi'
        };
        return descriptions[agentUsed] || 'Agent specialist';
    }

    formatSpecialistData(agentUsed, specialistData) {
        if (!specialistData) return '<span class="data-value">Data tidak tersedia</span>';
        
        switch(agentUsed) {
            case 'music':
                const recommendations = specialistData.recommendations || [];
                return `
                    <div class="step-data">
                        <span class="data-label">🎼 Spotify API:</span> 
                        <span class="data-value">${recommendations.length} lagu ditemukan</span>
                    </div>
                    <div class="step-data">
                        <span class="data-label">🎹 Genre:</span> 
                        <span class="data-value">${specialistData.genre || 'N/A'}</span>
                    </div>
                    <div class="step-data">
                        <span class="data-label">📊 Total hasil:</span> 
                        <span class="data-value">${specialistData.total_found || 0} lagu</span>
                    </div>
                `;
            case 'entertainment':
                const content = specialistData.content || {};
                return `
                    <div class="step-data">
                        <span class="data-label">🎭 Giphy API:</span> 
                        <span class="data-value">${content.gifs?.length || 0} GIF</span>
                    </div>
                    <div class="step-data">
                        <span class="data-label">😂 Jokes:</span> 
                        <span class="data-value">${content.jokes?.length || 0} lelucon</span>
                    </div>
                    <div class="step-data">
                        <span class="data-label">📺 Total konten:</span> 
                        <span class="data-value">${specialistData.total_items || 0} item</span>
                    </div>
                `;
            case 'relaxation':
                return `
                    <div class="step-data">
                        <span class="data-label">🧘 Aktivitas:</span> 
                        <span class="data-value">${specialistData.activities?.length || 0} rekomendasi</span>
                    </div>
                    <div class="step-data">
                        <span class="data-label">🌬️ Teknik pernapasan:</span> 
                        <span class="data-value">${specialistData.breathing_exercises?.length || 0} teknik</span>
                    </div>
                    <div class="step-data">
                        <span class="data-label">💡 Tips:</span> 
                        <span class="data-value">${specialistData.relaxation_tips?.length || 0} tips</span>
                    </div>
                `;
            case 'reflection':
                return `
                    <div class="step-data">
                        <span class="data-label">🤖 Groq LLM:</span> 
                        <span class="data-value">Respons reflektif</span>
                    </div>
                    <div class="step-data">
                        <span class="data-label">💬 Mode:</span> 
                        <span class="data-value">Percakapan mendalam</span>
                    </div>
                    <div class="step-data">
                        <span class="data-label">❤️ Fokus:</span> 
                        <span class="data-value">Dukungan emosional</span>
                    </div>
                `;
            default:
                return '<span class="data-value">Data specialist tidak tersedia</span>';
        }
    }
}

// Global instance
let hatiChat;

// Global functions for HTML event handlers
function sendMessage() {
    hatiChat.sendMessage();
}

function sendQuickMessage(message) {
    hatiChat.sendQuickMessage(message);
}

function handleKeyPress(event) {
    hatiChat.handleKeyPress(event);
}

function autoResize(textarea) {
    hatiChat.autoResize(textarea);
}

function toggleSettings() {
    hatiChat.toggleSettings();
}

function testConnection() {
    hatiChat.testConnection();
}

// Ambient Music System
class AmbientMusic {
    constructor() {
        this.audio = document.getElementById('ambientAudio');
        this.source = document.getElementById('ambientSource');
        this.isPlaying = false;
        this.currentPreset = 'rain';
        this.volume = 0.3;
        
        this.presets = {
            rain: {
                name: 'Rain',
                url: 'https://cdn.pixabay.com/download/audio/2024/10/30/audio_42e6870f29.mp3',
                icon: 'fas fa-cloud-rain'
            },
            forest: {
                name: 'Forest',
                url: 'https://cdn.freesound.org/previews/565/565564_8462944-lq.mp3',
                icon: 'fas fa-tree'
            },
            cafe: {
                name: 'Cafe',
                url: 'https://assets.mixkit.co/active_storage/sfx/452/452.wav',
                icon: 'fas fa-coffee'
            },
            ocean: {
                name: 'Ocean',
                url: 'https://assets.mixkit.co/active_storage/sfx/1195/1195.wav',
                icon: 'fas fa-water'
            },
            city: {
                name: 'City',
                url: 'https://cdn.freesound.org/previews/417/417443_7515445-lq.mp3',
                icon: 'fas fa-city'
            }
        };
        
        this.initializeAudio();
    }
    
    initializeAudio() {
        this.audio.volume = this.volume;
        this.setPreset(this.currentPreset);
        
        // Handle audio events
        this.audio.addEventListener('canplay', () => {
            console.log('Ambient audio ready');
        });
        
        this.audio.addEventListener('error', (e) => {
            console.warn('Ambient audio error:', e);
            this.fallbackToSilence();
        });
    }
    
    fallbackToSilence() {
        // Create silent audio as fallback
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioCtx.createOscillator();
        const gainNode = audioCtx.createGain();
        
        gainNode.gain.value = 0; // Silent
        oscillator.connect(gainNode);
        gainNode.connect(audioCtx.destination);
        oscillator.start();
    }
    
    toggle() {
        if (this.isPlaying) {
            this.stop();
        } else {
            this.play();
        }
    }
    
    play() {
        this.audio.play().then(() => {
            this.isPlaying = true;
            this.updateUI();
        }).catch(e => {
            console.warn('Could not play ambient audio:', e);
            this.fallbackToSilence();
        });
    }
    
    stop() {
        this.audio.pause();
        this.isPlaying = false;
        this.updateUI();
    }
    
    setPreset(preset) {
        if (this.presets[preset]) {
            this.currentPreset = preset;
            this.source.src = this.presets[preset].url;
            this.audio.load();
            this.updatePresetUI();
            
            if (this.isPlaying) {
                setTimeout(() => this.play(), 100);
            }
        }
    }
    
    setVolume(volume) {
        this.volume = volume / 100;
        this.audio.volume = this.volume;
    }
    
    updateUI() {
        const toggleBtn = document.getElementById('ambientToggle');
        const icon = toggleBtn.querySelector('i');
        const text = toggleBtn.querySelector('span');
        
        if (this.isPlaying) {
            toggleBtn.classList.add('active');
            icon.className = 'fas fa-pause';
            text.textContent = 'Playing';
        } else {
            toggleBtn.classList.remove('active');
            icon.className = 'fas fa-music';
            text.textContent = 'Ambient Music';
        }
    }
    
    updatePresetUI() {
        document.querySelectorAll('.preset-btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.dataset.preset === this.currentPreset) {
                btn.classList.add('active');
            }
        });
    }
}

// Global ambient music instance
let ambientMusic;

// Global ambient music functions
function toggleAmbientMusic() {
    const options = document.getElementById('ambientOptions');
    const isVisible = options.style.display !== 'none';
    
    if (isVisible) {
        options.style.display = 'none';
    } else {
        options.style.display = 'block';
        if (!ambientMusic.isPlaying) {
            ambientMusic.toggle();
        }
    }
}

function setAmbientPreset(preset) {
    ambientMusic.setPreset(preset);
}

function setAmbientVolume(volume) {
    ambientMusic.setVolume(volume);
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    hatiChat = new HatiChat();
    ambientMusic = new AmbientMusic();
    
    // Auto-save settings when changed
    document.getElementById('backendUrl').addEventListener('change', () => hatiChat.saveSettings());
    document.getElementById('debugMode').addEventListener('change', () => hatiChat.saveSettings());
    
    // Close ambient options when clicking outside
    document.addEventListener('click', function(e) {
        const ambientControls = document.querySelector('.ambient-controls');
        const ambientOptions = document.getElementById('ambientOptions');
        
        if (!ambientControls.contains(e.target) && ambientOptions.style.display !== 'none') {
            ambientOptions.style.display = 'none';
        }
    });
});

// Handle page visibility changes
document.addEventListener('visibilitychange', function() {
    if (!document.hidden && hatiChat) {
        // Check connection when page becomes visible
        hatiChat.checkConnection();
    }
});
