// Global variables
let currentResults = null;
let originalResults = null;

// DOM Elements
const textInput = document.getElementById('text-input');
const fileInput = document.getElementById('file-input');
const fileUploadArea = document.getElementById('file-upload-area');
const extractBtn = document.getElementById('extract-btn');
const sampleTextBtn = document.getElementById('sample-text-btn');
const clearBtn = document.getElementById('clear-btn');
const resultsSection = document.getElementById('results-section');
const loadingOverlay = document.getElementById('loading-overlay');

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    initializeFileUpload();
});

// Event Listeners
function initializeEventListeners() {
    extractBtn.addEventListener('click', handleExtraction);
    sampleTextBtn.addEventListener('click', loadSampleText);
    clearBtn.addEventListener('click', clearAll);
    
    // Real-time text length counter
    textInput.addEventListener('input', function() {
        const length = this.value.length;
        if (length > 0) {
            extractBtn.disabled = false;
        } else {
            extractBtn.disabled = true;
        }
    });
}

// File Upload Functionality
function initializeFileUpload() {
    // File input change
    fileInput.addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            handleFileUpload(e.target.files[0]);
        }
    });

    // Drag and drop
    fileUploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        this.classList.add('dragover');
    });

    fileUploadArea.addEventListener('dragleave', function(e) {
        e.preventDefault();
        this.classList.remove('dragover');
    });

    fileUploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        this.classList.remove('dragover');
        
        if (e.dataTransfer.files.length > 0) {
            handleFileUpload(e.dataTransfer.files[0]);
        }
    });

    // Click to upload
    // fileUploadArea.addEventListener('click', function() {
    //     fileInput.click();
    // });
}

// Handle file upload
async function handleFileUpload(file) {
    const maxSize = 16 * 1024 * 1024; // 16MB
    const allowedTypes = ['text/plain', 'application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
    
    if (file.size > maxSize) {
        showToast('File too large. Maximum size is 16MB.', 'error');
        return;
    }
    
    if (!allowedTypes.includes(file.type) && !file.name.toLowerCase().endsWith('.txt')) {
        showToast('Unsupported file type. Please upload TXT, PDF, or DOCX files.', 'error');
        return;
    }
    
    showLoading(true);
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (response.ok) {
            textInput.value = result.full_content;
            showToast(`File "${result.filename}" uploaded successfully!`, 'success');
            extractBtn.disabled = false;
        } else {
            throw new Error(result.error || 'Upload failed');
        }
    } catch (error) {
        console.error('Upload error:', error);
        showToast(`Upload failed: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

// Load sample text
async function loadSampleText() {
    try {
        showLoading(true);
        
        const response = await fetch('/api/sample-text');
        const data = await response.json();
        
        if (response.ok) {
            textInput.value = data.text;
            extractBtn.disabled = false;
            showToast('Sample text loaded!', 'success');
        } else {
            throw new Error(data.error || 'Failed to load sample text');
        }
    } catch (error) {
        console.error('Error loading sample text:', error);
        showToast(`Failed to load sample text: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

// Clear all inputs and results
function clearAll() {
    textInput.value = '';
    resultsSection.style.display = 'none';
    currentResults = null;
    originalResults = null;
    extractBtn.disabled = true;
    
    // Reset checkboxes
    document.querySelectorAll('#entity-checkboxes input[type="checkbox"]').forEach(cb => {
        cb.checked = true;
    });
    document.getElementById('extract-events').checked = true;
    
    showToast('Cleared all data', 'info');
}

// Handle extraction
async function handleExtraction() {
    const text = textInput.value.trim();
    
    if (!text) {
        showToast('Please enter some text to analyze', 'error');
        return;
    }
    
    // Get selected entity types
    const selectedTypes = [];
    document.querySelectorAll('#entity-checkboxes input[type="checkbox"]:checked').forEach(cb => {
        selectedTypes.push(cb.value);
    });
    
    const extractEvents = document.getElementById('extract-events').checked;
    
    showLoading(true);
    
    try {
        const response = await fetch('/api/extract', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                text: text,
                entity_types: selectedTypes,
                extract_events: extractEvents
            })
        });
        
        const results = await response.json();
        
        if (response.ok) {
            currentResults = results;
            originalResults = JSON.parse(JSON.stringify(results)); // Deep copy
            displayResults(results);
            showToast('Extraction completed successfully!', 'success');
        } else {
            throw new Error(results.error || 'Extraction failed');
        }
    } catch (error) {
        console.error('Extraction error:', error);
        showToast(`Extraction failed: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

// Display results
function displayResults(results) {
    resultsSection.style.display = 'block';
    
    // Update statistics
    updateStatistics(results);
    
    // Display highlighted text
    document.getElementById('highlighted-text').innerHTML = results.highlighted_text;
    
    // Display detailed results
    displayEntities(results.entities);
    displayEvents(results.events);
    
    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

// Update statistics panel
function updateStatistics(results) {
    const stats = results.statistics;
    const metadata = results.metadata;
    
    document.getElementById('entity-count').textContent = stats.total_entities || 0;
    document.getElementById('event-count').textContent = stats.total_events || 0;
    document.getElementById('processing-time').textContent = metadata.processing_time || '0';
    
    // Update count badges
    document.getElementById('entities-count-badge').textContent = stats.total_entities || 0;
    document.getElementById('events-count-badge').textContent = stats.total_events || 0;
}

// Display entities
function displayEntities(entities) {
    const entitiesList = document.getElementById('entities-list');
    entitiesList.innerHTML = '';
    
    if (entities.length === 0) {
        entitiesList.innerHTML = '<p class="no-results">No entities found.</p>';
        return;
    }
    
    entities.forEach(entity => {
        const entityElement = createEntityElement(entity);
        entitiesList.appendChild(entityElement);
    });
}

// Display events
function displayEvents(events) {
    const eventsList = document.getElementById('events-list');
    eventsList.innerHTML = '';
    
    if (events.length === 0) {
        eventsList.innerHTML = '<p class="no-results">No events found.</p>';
        return;
    }
    
    events.forEach(event => {
        const eventElement = createEventElement(event);
        eventsList.appendChild(eventElement);
    });
}

// Create entity element
function createEntityElement(entity) {
    const div = document.createElement('div');
    div.className = 'result-item';
    div.dataset.type = entity.type;
    div.dataset.confidence = entity.confidence;
    
    const entityColor = getEntityColor(entity.type);
    
    div.innerHTML = `
        <div class="result-header">
            <span class="result-text">${escapeHtml(entity.text)}</span>
            <span class="result-type" style="background-color: ${entityColor}">${entity.type}</span>
        </div>
        <div class="result-details">
            <div><strong>Position:</strong> ${entity.start} - ${entity.end}</div>
            <div><strong>Confidence:</strong> ${(entity.confidence * 100).toFixed(1)}%</div>
            ${entity.context ? `<div class="result-context">"${escapeHtml(entity.context)}"</div>` : ''}
        </div>
        <div class="confidence-bar">
            <div class="confidence-fill" style="width: ${entity.confidence * 100}%"></div>
        </div>
    `;
    
    return div;
}

// Create event element
function createEventElement(event) {
    const div = document.createElement('div');
    div.className = 'result-item';
    div.dataset.type = event.type;
    div.dataset.confidence = event.confidence;
    
    let attributesHtml = '';
    if (event.attributes && Object.keys(event.attributes).length > 0) {
        attributesHtml = '<div><strong>Attributes:</strong><ul>';
        for (const [key, value] of Object.entries(event.attributes)) {
            if (value) {
                attributesHtml += `<li><strong>${key.replace(/_/g, ' ').toUpperCase()}:</strong> ${escapeHtml(value)}</li>`;
            }
        }
        attributesHtml += '</ul></div>';
    }
    
    div.innerHTML = `
        <div class="result-header">
            <span class="result-text">${escapeHtml(event.text)}</span>
            <span class="result-type" style="background-color: #DDA0DD">${event.type}</span>
        </div>
        <div class="result-details">
            <div><strong>Position:</strong> ${event.start} - ${event.end}</div>
            <div><strong>Confidence:</strong> ${(event.confidence * 100).toFixed(1)}%</div>
            ${attributesHtml}
            ${event.context ? `<div class="result-context">"${escapeHtml(event.context)}"</div>` : ''}
        </div>
        <div class="confidence-bar">
            <div class="confidence-fill" style="width: ${event.confidence * 100}%"></div>
        </div>
    `;
    
    return div;
}

// Get entity color from configuration
function getEntityColor(entityType) {
    const entityColors = {
        'PERSON': '#FF6B6B',
        'ORGANIZATION': '#4ECDC4',
        'LOCATION': '#45B7D1',
        'DATE': '#96CEB4',
        'MONEY': '#FFEAA7',
        'EVENT': '#DDA0DD',
        'CONTACT': '#FDA7DF'
    };
    return entityColors[entityType] || '#CCCCCC';
}

// Tab functionality
function toggleTab(tabId) {
    const tabContent = document.getElementById(tabId);
    const tabArrow = tabContent.previousElementSibling.querySelector('.tab-arrow');
    
    if (tabContent.classList.contains('active')) {
        tabContent.classList.remove('active');
        tabArrow.style.transform = 'rotate(0deg)';
    } else {
        tabContent.classList.add('active');
        tabArrow.style.transform = 'rotate(180deg)';
    }
}

// Filter functionality
function filterResults(filterType) {
    if (!currentResults) return;
    
    // Update active filter button
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');
    
    const entitiesTab = document.getElementById('entities-tab');
    const eventsTab = document.getElementById('events-tab');
    
    switch (filterType) {
        case 'all':
            entitiesTab.style.display = 'block';
            eventsTab.style.display = 'block';
            break;
        case 'entities':
            entitiesTab.style.display = 'block';
            eventsTab.style.display = 'none';
            break;
        case 'events':
            entitiesTab.style.display = 'none';
            eventsTab.style.display = 'block';
            break;
    }
}

// Filter by confidence
function filterByConfidence(minConfidence) {
    if (!originalResults) return;
    
    document.getElementById('confidence-value').textContent = parseFloat(minConfidence).toFixed(1);
    
    // Filter entities and events
    const filteredEntities = originalResults.entities.filter(entity => 
        entity.confidence >= parseFloat(minConfidence)
    );
    
    const filteredEvents = originalResults.events.filter(event => 
        event.confidence >= parseFloat(minConfidence)
    );
    
    // Update current results
    currentResults = {
        ...originalResults,
        entities: filteredEntities,
        events: filteredEvents,
        statistics: {
            ...originalResults.statistics,
            total_entities: filteredEntities.length,
            total_events: filteredEvents.length
        }
    };
    
    // Update display
    updateStatistics(currentResults);
    displayEntities(filteredEntities);
    displayEvents(filteredEvents);
}

// Export functionality
async function exportResults(format) {
    if (!currentResults) {
        showToast('No results to export', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/export', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                format: format,
                results: currentResults
            })
        });
        
        if (response.ok) {
            if (format === 'json') {
                const data = await response.json();
                downloadFile(JSON.stringify(data, null, 2), `extraction_results.json`, 'application/json');
            } else {
                const data = await response.text();
                const contentType = response.headers.get('content-type');
                const filename = format === 'csv' ? 'extraction_results.csv' : 'extraction_report.txt';
                downloadFile(data, filename, contentType);
            }
            showToast(`Results exported as ${format.toUpperCase()}`, 'success');
        } else {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Export failed');
        }
    } catch (error) {
        console.error('Export error:', error);
        showToast(`Export failed: ${error.message}`, 'error');
    }
}

// Download file helper
function downloadFile(content, filename, contentType) {
    const blob = new Blob([content], { type: contentType });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
}

// Show/hide loading overlay
function showLoading(show) {
    loadingOverlay.style.display = show ? 'flex' : 'none';
}

// Toast notification system
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    
    toastContainer.appendChild(toast);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (toast.parentNode) {
            toast.parentNode.removeChild(toast);
        }
    }, 5000);
    
    // Remove on click
    toast.addEventListener('click', () => {
        if (toast.parentNode) {
            toast.parentNode.removeChild(toast);
        }
    });
}

// Utility function to escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize tabs as collapsed
document.addEventListener('DOMContentLoaded', function() {
    // Open entities tab by default
    setTimeout(() => {
        if (document.getElementById('entities-tab')) {
            toggleTab('entities-tab');
        }
    }, 100);
});

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl+Enter to extract
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        if (!extractBtn.disabled) {
            handleExtraction();
        }
    }
    
    // Ctrl+L to load sample
    if ((e.ctrlKey || e.metaKey) && e.key === 'l') {
        e.preventDefault();
        loadSampleText();
    }
    
    // Escape to clear
    if (e.key === 'Escape') {
        clearAll();
    }
});

// Add tooltips for highlighted entities
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('highlight')) {
        const type = e.target.dataset.type;
        const confidence = e.target.dataset.confidence;
        showToast(`${type} (Confidence: ${(confidence * 100).toFixed(1)}%)`, 'info');
    }
});

// Performance monitoring
let performanceMetrics = {
    extractionTimes: [],
    averageTime: 0
};

function updatePerformanceMetrics(time) {
    performanceMetrics.extractionTimes.push(time);
    if (performanceMetrics.extractionTimes.length > 10) {
        performanceMetrics.extractionTimes.shift();
    }
    
    const sum = performanceMetrics.extractionTimes.reduce((a, b) => a + b, 0);
    performanceMetrics.averageTime = sum / performanceMetrics.extractionTimes.length;
    
    console.log(`Performance: Current: ${time}s, Average: ${performanceMetrics.averageTime.toFixed(3)}s`);
}
