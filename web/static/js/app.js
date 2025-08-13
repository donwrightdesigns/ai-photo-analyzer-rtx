document.addEventListener('DOMContentLoaded', function() {
    const socket = io();              
    const directoryPathInput = document.getElementById('directory-path');
    const startButton = document.getElementById('start-btn');
    const stopButton = document.getElementById('stop-btn');
    const browseButton = document.getElementById('browse-btn');
    const modelStatusDiv = document.getElementById('model-status');
    const progressInfoDiv = document.getElementById('progress-info');
    const progressBar = document.getElementById('progress-bar');
    const currentImage = document.getElementById('current-image');
    const resultsContainer = document.getElementById('results-container');
    const resultTemplate = document.getElementById('result-template');
    
    // Model selection elements - updated for 3-model system
    const modelRadios = document.querySelectorAll('input[name="model-type"]');
    const ollamaSettings = document.getElementById('ollama-settings');
    const geminiSettings = document.getElementById('gemini-settings');
    const bakllavaSettings = document.getElementById('bakllava-settings');
    const ollamaModelSelect = document.getElementById('ollama-model-select');
    const promptProfileSelect = document.getElementById('prompt-profile');
    const profileDescription = document.getElementById('profile-description');
    const apiKeyInput = document.getElementById('api-key');
    const toggleApiKeyBtn = document.getElementById('toggle-api-key');
    const downloadModelBtn = document.getElementById('download-model-btn');

    // Load prompt profiles
    fetch('/api/prompt_profiles')
        .then(response => response.json())
        .then(data => {
            // Update profile description
            updateProfileDescription(data.current);
        })
        .catch(error => console.error('Failed to load prompt profiles:', error));

    // Fetch model status on page load
    fetch('/api/model_status')
        .then(response => response.json())
        .then(data => {
            if(data.success && data.ollama_running) {
                modelStatusDiv.innerHTML = `<i class="fas fa-check-circle text-success me-2"></i>Ollama running - ${data.models.length} model(s) available`;
                modelStatusDiv.className = 'alert alert-success';
            } else {
                modelStatusDiv.innerHTML = `<i class="fas fa-exclamation-triangle text-warning me-2"></i>Ollama not detected (BakLLaVA and Gemini still available)`;
                modelStatusDiv.className = 'alert alert-warning';
            }
            validateForm();
        })
        .catch(error => {
            modelStatusDiv.innerHTML = `<i class="fas fa-times-circle text-danger me-2"></i>Unable to check model status`;
            modelStatusDiv.className = 'alert alert-danger';
            validateForm();
        });
    
    browseButton.addEventListener('click', () => {
        window.alert('Directory browsing is not supported directly via browser in this demo.');
    });

    // Handle model type changes for 3-model system
    modelRadios.forEach(radio => {
        radio.addEventListener('change', () => {
            handleModelTypeChange(radio.value);
            validateForm();
        });
    });

    function handleModelTypeChange(modelType) {
        // Hide all settings
        ollamaSettings.style.display = 'none';
        geminiSettings.style.display = 'none';
        bakllavaSettings.style.display = 'none';

        // Show relevant settings
        switch (modelType) {
            case 'ollama':
                ollamaSettings.style.display = 'block';
                break;
            case 'gemini':
                geminiSettings.style.display = 'block';
                break;
            case 'bakllava':
                bakllavaSettings.style.display = 'block';
                break;
        }
    }

    if (toggleApiKeyBtn) {
        toggleApiKeyBtn.addEventListener('click', () => {
            const type = apiKeyInput.type === 'password' ? 'text' : 'password';
            apiKeyInput.type = type;
            toggleApiKeyBtn.innerHTML = type === 'password' ? '<i class="fas fa-eye"></i>' : '<i class="fas fa-eye-slash"></i>';
        });
    }

    // Prompt profile selection
    if (promptProfileSelect) {
        promptProfileSelect.addEventListener('change', (e) => {
            setPromptProfile(e.target.value);
        });
    }

    function updateProfileDescription(profileKey) {
        const descriptions = {
            'professional_art_critic': 'Gallery curator perspective focusing on artistic merit and technical excellence',
            'family_archivist': 'Personal photo organizer focused on emotional value and family memories',
            'commercial_photographer': 'Industry professional evaluating marketability and client appeal',
            'social_media_curator': 'Digital content creator focused on engagement and shareability',
            'documentary_journalist': 'Photojournalist perspective emphasizing story and authenticity',
            'travel_blogger': 'Travel photographer focused on destination appeal and wanderlust'
        };
        
        if (profileDescription && descriptions[profileKey]) {
            profileDescription.textContent = descriptions[profileKey];
        }
    }

    function setPromptProfile(profileKey) {
        fetch('/api/set_prompt_profile', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ profile_key: profileKey })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateProfileDescription(profileKey);
            }
        })
        .catch(error => console.error('Failed to set prompt profile:', error));
    }

    if (downloadModelBtn) {
        downloadModelBtn.addEventListener('click', () => {
            const modelName = ollamaModelSelect.value;
            downloadModelBtn.disabled = true;
            downloadModelBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Downloading...';
            
            fetch('/api/download_model', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ model_name: modelName })
            })
            .then(response => response.json())
            .then(data => {
                if(data.success) {
                    alert('Model downloaded successfully: ' + data.message);
                } else {
                    alert('Failed to download model: ' + data.error);
                }
            })
            .finally(() => {
                downloadModelBtn.disabled = false;
                downloadModelBtn.innerHTML = '<i class="fas fa-download me-1"></i>Download Model';
            });
        });
    }

    // Form validation
    function validateForm() {
        const directoryPath = directoryPathInput.value.trim();
        const selectedModel = document.querySelector('input[name="model-type"]:checked');
        
        let isValid = directoryPath.length > 0 && selectedModel;
        
        // Additional validation for Gemini
        if (selectedModel && selectedModel.value === 'gemini') {
            const apiKey = apiKeyInput.value.trim();
            isValid = isValid && apiKey.length > 0;
        }
        
        startButton.disabled = !isValid;
    }

    // Add validation listeners
    directoryPathInput.addEventListener('input', validateForm);
    if (apiKeyInput) {
        apiKeyInput.addEventListener('input', validateForm);
    }

    // Start analysis
    startButton.addEventListener('click', () => {
        const directoryPath = directoryPathInput.value.trim();
        const writeExif = document.getElementById('write-exif').checked;
        const selectedModel = document.querySelector('input[name="model-type"]:checked');
        const modelType = selectedModel ? selectedModel.value : 'gemini';
        const apiKey = apiKeyInput.value;

        fetch('/api/start_processing', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ directory_path: directoryPath, write_exif: writeExif, model_type: modelType, api_key: apiKey })
        })
        .then(response => response.json())
        .then(data => {
            if(data.success) {
                startButton.disabled = true;
                stopButton.disabled = false;
                resultsContainer.innerHTML = '';
                progressBar.style.width = '0%';
                progressInfoDiv.textContent = "Starting processing...";
            } else {
                alert('Failed to start processing: ' + data.error);
            }
        });
    });

    // Stop analysis
    stopButton.addEventListener('click', () => {
        fetch('/api/stop_processing', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            if(data.success) {
                stopButton.disabled = true;
                startButton.disabled = false;
                progressInfoDiv.textContent = "Stopped.";
            }
        });
    });

    // Socket event listeners
    socket.on('progress_update', data => {
        progressBar.style.width = (data.processed / data.total * 100) + '%';
        progressInfoDiv.textContent = `${data.processed} of ${data.total} images processed.`;
        currentImage.textContent = data.current_image;
    });

    socket.on('image_processed', data => {
        const clone = resultTemplate.content.cloneNode(true);
        clone.querySelector('.image-preview small').textContent = data.result.image_name;
        clone.querySelector('.category-badge').textContent = data.result.analysis.category;
        clone.querySelector('.subcategory-badge').textContent = data.result.analysis.subcategory;
        clone.querySelector('.stars').textContent = `${data.result.analysis.score} Stars`;
        clone.querySelector('.tags-container').textContent = data.result.analysis.tags.join(', ');
        clone.querySelector('.critique').textContent = data.result.analysis.critique;
        resultsContainer.appendChild(clone);
    });

    socket.on('processing_complete', data => {
        stopButton.disabled = true;
        startButton.disabled = false;
        progressInfoDiv.innerHTML = `<p class="mb-0 text-success"><i class="fas fa-check-circle me-2"></i>Processing complete! ${data.total_processed} images analyzed.</p>`;
    });

    // Initialize model type display
    const defaultModel = document.querySelector('input[name="model-type"]:checked');
    if (defaultModel) {
        handleModelTypeChange(defaultModel.value);
    }
    
    // Initial form validation
    validateForm();
});
