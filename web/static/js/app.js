document.addEventListener('DOMContentLoaded', () => {
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
    
    // Model selection elements
    const modelLocalRadio = document.getElementById('model-local');
    const modelCloudRadio = document.getElementById('model-cloud');
    const localSettings = document.getElementById('local-settings');
    const cloudSettings = document.getElementById('cloud-settings');
    const localModelSelect = document.getElementById('local-model-select');
    const apiKeyInput = document.getElementById('api-key');
    const toggleApiKeyBtn = document.getElementById('toggle-api-key');
    const downloadModelBtn = document.getElementById('download-model-btn');

    // Fetch model status on page load
    fetch('/api/model_status')
        .then(response => response.json())
        .then(data => {
            if(data.success) {
                modelStatusDiv.textContent = `Model is ${data.llava_available ? 'available' : 'unavailable'}`;
                modelStatusDiv.classList.toggle('alert-success', data.llava_available);
                modelStatusDiv.classList.toggle('alert-danger', !data.llava_available);
                startButton.disabled = !data.llava_available;
            } else {
                modelStatusDiv.textContent = "Failed to check model status";
            }
        });
    
    browseButton.addEventListener('click', () => {
        window.alert('Directory browsing is not supported directly via browser in this demo.');
    });

    modelLocalRadio.addEventListener('change', () => {
        localSettings.style.display = 'block';
        cloudSettings.style.display = 'none';
    });

    modelCloudRadio.addEventListener('change', () => {
        localSettings.style.display = 'none';
        cloudSettings.style.display = 'block';
    });

    toggleApiKeyBtn.addEventListener('click', () => {
        const type = apiKeyInput.type === 'password' ? 'text' : 'password';
        apiKeyInput.type = type;
        toggleApiKeyBtn.innerHTML = type === 'password' ? '<i class="fas fa-eye"></i>' : '<i class="fas fa-eye-slash"></i>';
    });

    downloadModelBtn.addEventListener('click', () => {
        const modelName = localModelSelect.value;
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

    // Start analysis
    startButton.addEventListener('click', () => {
        const directoryPath = directoryPathInput.value;
        const writeExif = document.getElementById('write-exif').checked;
        const modelType = modelLocalRadio.checked ? 'local' : 'cloud';
        const apiKey = apiKeyInput.value;

        fetch('/api/start_processing', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ directory_path: directoryPath, write_exif: writeExif, model_type: modelType, api_key: apiKey })
        })
        .then(response => response.json())
        .then(data => {
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
        progressInfoDiv.textContent = "Processing completed.";
    });
});
