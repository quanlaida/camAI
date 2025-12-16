// Global variables
let currentPage = 1;
let detectionsPerPage = 10;
let currentFilter = '';
let currentClientFilter = '';
let currentTab = 'detections';

// Alert system - Track last detection count and IDs
let lastDetectionCount = 0;
let lastDetectionIds = new Set();
let notificationPermissionGranted = false;


// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', function () {
    initializeApp();
});

function initializeApp() {
    // Set up event listeners - check if elements exist first
    const refreshBtn = document.getElementById('refresh-btn');
    const classFilter = document.getElementById('class-filter');
    const clientFilter = document.getElementById('client-filter');
    const limitSelect = document.getElementById('limit-select');
    const prevPage = document.getElementById('prev-page');
    const nextPage = document.getElementById('next-page');
    const addClientBtn = document.getElementById('add-client-btn');
    const refreshClientsBtn = document.getElementById('refresh-clients-btn');
    
    if (refreshBtn) refreshBtn.addEventListener('click', refreshData);
    if (classFilter) classFilter.addEventListener('change', handleFilterChange);
    if (clientFilter) clientFilter.addEventListener('change', handleClientFilterChange);
    if (limitSelect) limitSelect.addEventListener('change', handleLimitChange);
    if (prevPage) prevPage.addEventListener('click', () => changePage(-1));
    if (nextPage) nextPage.addEventListener('click', () => changePage(1));
    if (addClientBtn) addClientBtn.addEventListener('click', () => openClientModal());
    if (refreshClientsBtn) refreshClientsBtn.addEventListener('click', loadClients);

    // Tab switching
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => switchTab(e.target.dataset.tab));
    });

    // Detection page stream selector
    const detectionStreamSelect = document.getElementById('detection-stream-client-select');
    if (detectionStreamSelect) {
        detectionStreamSelect.addEventListener('change', handleDetectionStreamChange);
    }
    
    // Detection page refresh button
    const detectionRefreshBtn = document.getElementById('detection-refresh-btn');
    if (detectionRefreshBtn) {
        detectionRefreshBtn.addEventListener('click', () => {
            loadDetections();
            loadDetectionStreamClients();
        });
    }

    // Set up modals first
    setupModal();
    setupClientModal();

    // Request notification permission
    requestNotificationPermission();

    // Load alert settings khi trang load
    loadAlertSettings();

    // Event listener cho nút "Lưu Email"
    const saveEmailBtn = document.getElementById('save-email-btn');
    if (saveEmailBtn) {
        saveEmailBtn.addEventListener('click', saveAlertSettings);
    }

    // Event listener cho checkbox "Bật cảnh báo email" - tự động lưu khi thay đổi
    const emailCheckbox = document.getElementById('email-enabled-checkbox');
    if (emailCheckbox) {
        emailCheckbox.addEventListener('change', () => {
            // Tự động lưu khi checkbox thay đổi
            saveAlertSettings();
        });
    }

    // Event listener cho nút "Test Email"
    const testEmailBtn = document.getElementById('test-email-btn');
    if (testEmailBtn) {
        testEmailBtn.addEventListener('click', testEmail);
    }

    // Load initial data - luôn trigger switchTab để đảm bảo load đúng
    // Vì tab detection là tab mặc định, cần trigger switchTab để load data
    // Tăng delay để tránh quá tải khi load trang
    setTimeout(() => {
        switchTab('detections');
    }, 300);
}

function setupModal() {
    const modal = document.getElementById('detail-modal');
    const closeBtn = document.querySelector('.close');

    closeBtn.onclick = function () {
        modal.style.display = 'none';
    };

    window.onclick = function (event) {
        if (event.target == modal) {
            modal.style.display = 'none';
        }
    };
}

function handleFilterChange() {
    currentFilter = document.getElementById('class-filter').value;
    currentPage = 1;
    loadDetections();
}

function handleClientFilterChange() {
    currentClientFilter = document.getElementById('client-filter').value;
    currentPage = 1;
    loadDetections();
}

function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.style.display = 'none';
    });
    document.getElementById(`${tabName}-tab`).style.display = 'block';

    // Update controls
    document.getElementById('detections-controls').style.display = tabName === 'detections' ? 'flex' : 'none';
    document.getElementById('clients-controls').style.display = tabName === 'clients' ? 'flex' : 'none';

    // Load data when switching tabs - Tối ưu: load tuần tự thay vì parallel để tránh quá tải
    if (tabName === 'detections') {
        // Load stats trước (nhẹ nhất)
        loadStats();
        // Sau đó load clients, rồi mới load detections và stream
        loadClients().then(() => {
            // Delay nhỏ để tránh quá tải
            setTimeout(() => {
                loadDetections();
                loadDetectionStreamClients();
            }, 100);
        });
    } else if (tabName === 'clients') {
        loadClients();
    }

    currentTab = tabName;
}

function handleLimitChange() {
    detectionsPerPage = parseInt(document.getElementById('limit-select').value);
    currentPage = 1;
    loadDetections();
}

function refreshData() {
    // Tối ưu: chỉ refresh data của tab hiện tại, không refresh tất cả
    if (currentTab === 'detections') {
        loadStats();
        loadDetections();
        // Không load clients mỗi lần refresh (chỉ load khi cần)
    } else if (currentTab === 'clients') {
        loadClients();
    }
}

function changePage(direction) {
    currentPage += direction;
    loadDetections();
    updatePaginationButtons();
}

function updatePaginationButtons() {
    const prevBtn = document.getElementById('prev-page');
    const nextBtn = document.getElementById('next-page');

    prevBtn.disabled = currentPage <= 1;

    // We'll enable next button by default, disable it if we get fewer results than expected
    nextBtn.disabled = false;
}

async function loadStats() {
    try {
        const response = await fetch('/api/detections/stats');
        const stats = await response.json();

        const newDetectionCount = stats.total_detections;
        
        // Check for new detections
        if (lastDetectionCount > 0 && newDetectionCount > lastDetectionCount) {
            const newDetections = newDetectionCount - lastDetectionCount;
            await checkAndAlertNewDetections(newDetections);
        }

        lastDetectionCount = newDetectionCount;

        document.getElementById('total-detections').textContent = stats.total_detections;
        document.getElementById('recent-detections').textContent = stats.recent_detections;
        document.getElementById('active-clients').textContent = stats.active_clients;
        document.getElementById('active-classes').textContent = Object.keys(stats.detections_by_class).length;

        // Update filter dropdowns
        updateClassFilter(stats.detections_by_class);
        updateClientFilter(stats.clients);

    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

function updateClassFilter(classCounts) {
    const filterSelect = document.getElementById('class-filter');
    const currentValue = filterSelect.value;

    // Clear existing options except "All Classes"
    while (filterSelect.children.length > 1) {
        filterSelect.removeChild(filterSelect.lastChild);
    }

    // Add class options
    Object.keys(classCounts).sort().forEach(className => {
        const option = document.createElement('option');
        option.value = className;
        option.textContent = `${className} (${classCounts[className]})`;
        filterSelect.appendChild(option);
    });

    // Restore previous selection if it still exists
    if (currentValue && filterSelect.querySelector(`option[value="${currentValue}"]`)) {
        filterSelect.value = currentValue;
    }
}

function updateClientFilter(clients) {
    const filterSelect = document.getElementById('client-filter');
    const currentValue = filterSelect.value;

    // Clear existing options except "All Clients"
    while (filterSelect.children.length > 1) {
        filterSelect.removeChild(filterSelect.lastChild);
    }

    // Add client options
    Object.keys(clients).sort().forEach(clientName => {
        const client = clients[clientName];
        const option = document.createElement('option');
        option.value = client.id;
        option.textContent = `${clientName} (${client.detections} detections)`;
        filterSelect.appendChild(option);
    });

    // Restore previous selection if it still exists
    if (currentValue && filterSelect.querySelector(`option[value="${currentValue}"]`)) {
        filterSelect.value = currentValue;
    }
}

async function loadDetections() {
    try {
        const offset = (currentPage - 1) * detectionsPerPage;
        let url = `/api/detections?limit=${detectionsPerPage}&offset=${offset}`;

        if (currentFilter) {
            url += `&class=${encodeURIComponent(currentFilter)}`;
        }

        if (currentClientFilter) {
            url += `&client_id=${encodeURIComponent(currentClientFilter)}`;
        }

        const response = await fetch(url);
        const detections = await response.json();

        // Check for new detections by comparing IDs
        if (lastDetectionIds.size > 0 && detections.length > 0) {
            const currentIds = new Set(detections.map(d => d.id));
            const newDetections = detections.filter(d => !lastDetectionIds.has(d.id));
            
            if (newDetections.length > 0) {
                await checkAndAlertNewDetections(newDetections.length, newDetections[0]);
            }
            
            lastDetectionIds = currentIds;
        } else if (detections.length > 0) {
            // First load - initialize IDs
            lastDetectionIds = new Set(detections.map(d => d.id));
        }

        displayDetections(detections);

        // Check if we got fewer results than expected (indicates last page)
        if (detections.length < detectionsPerPage) {
            document.getElementById('next-page').disabled = true;
        }

        updatePaginationButtons();

    } catch (error) {
        console.error('Error loading detections:', error);
        document.getElementById('detections-body').innerHTML =
            '<tr><td colspan="6" style="text-align: center; color: #e74c3c;">Error loading detections</td></tr>';
    }
}

function displayDetections(detections) {
    const tbody = document.getElementById('detections-body');

    if (detections.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: #7f8c8d;">No detections found</td></tr>';
        return;
    }

    tbody.innerHTML = detections.map(detection => `
        <tr>
            <td>${formatTimestamp(detection.timestamp)}</td>
            <td>
                <span class="client-name">${detection.client ? detection.client.name : 'Unknown'}</span>
            </td>
            <td>
                <span class="class-name">${detection.class_name}</span>
            </td>
            <td>
                <span class="confidence ${getConfidenceClass(detection.confidence)}">
                    ${(detection.confidence * 100).toFixed(1)}%
                </span>
            </td>
            <td>
                <img src="/api/images/${detection.image_path}"
                     alt="Detection"
                     class="image-thumbnail"
                     onclick="showDetectionDetail(${detection.id})">
            </td>
            <td>
                <button class="view-btn" onclick="showDetectionDetail(${detection.id})">
                    View Details
                </button>
            </td>
        </tr>
    `).join('');
}

function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffHours = diffMs / (1000 * 60 * 60);

    if (diffHours < 24) {
        return date.toLocaleTimeString();
    } else {
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    }
}

function isClientOnline(updatedAt) {
    if (!updatedAt) return false;
    const now = new Date();
    const lastUpdate = new Date(updatedAt);
    const diffMinutes = (now - lastUpdate) / (1000 * 60);
    // Online nếu cập nhật trong vòng 2 phút
    return diffMinutes <= 2;
}

function getOnlineStatus(updatedAt) {
    if (!updatedAt) return { status: 'offline', text: 'Offline', class: 'offline' };
    const now = new Date();
    const lastUpdate = new Date(updatedAt);
    const diffMinutes = (now - lastUpdate) / (1000 * 60);
    
    if (diffMinutes <= 2) {
        return { status: 'online', text: 'Online', class: 'online' };
    } else if (diffMinutes <= 5) {
        return { status: 'warning', text: 'Cảnh báo', class: 'warning' };
    } else {
        return { status: 'offline', text: 'Offline', class: 'offline' };
    }
}

function getConfidenceClass(confidence) {
    if (confidence >= 0.7) return 'high';
    if (confidence >= 0.4) return 'medium';
    return 'low';
}

async function showDetectionDetail(detectionId) {
    try {
        const response = await fetch(`/api/detections/${detectionId}`);
        const detection = await response.json();

        const modal = document.getElementById('detail-modal');
        const modalContent = document.getElementById('modal-content');

        modalContent.innerHTML = `
            <h2>Detection Details</h2>
            <div class="detection-info">
                <div class="info-item">
                    <label>Detection ID:</label>
                    <span>${detection.id}</span>
                </div>
                <div class="info-item">
                    <label>Timestamp:</label>
                    <span>${formatTimestamp(detection.timestamp)}</span>
                </div>
                <div class="info-item">
                    <label>Client:</label>
                    <span>${detection.client ? detection.client.name : 'Unknown'}</span>
                </div>
                <div class="info-item">
                    <label>Class:</label>
                    <span>${detection.class_name}</span>
                </div>
                <div class="info-item">
                    <label>Confidence:</label>
                    <span class="confidence ${getConfidenceClass(detection.confidence)}">
                        ${(detection.confidence * 100).toFixed(1)}%
                    </span>
                </div>
                <div class="info-item">
                    <label>Bounding Box:</label>
                    <span>x: ${detection.bbox_x}, y: ${detection.bbox_y}, w: ${detection.bbox_width}, h: ${detection.bbox_height}</span>
                </div>
            </div>
            <img src="/api/images/${detection.image_path}"
                 alt="Detection Image"
                 class="modal-image">
        `;

        modal.style.display = 'block';

    } catch (error) {
        console.error('Error loading detection details:', error);
        alert('Error loading detection details');
    }
}

// Client management functions
// Detection page stream functions
function loadDetectionStreamClients() {
    fetch('/api/clients')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(clients => {
            const select = document.getElementById('detection-stream-client-select');
            if (!select) return;
            
            const currentValue = select.value;
            select.innerHTML = '<option value="">Chọn client...</option>';
            
            if (Array.isArray(clients) && clients.length > 0) {
                clients.forEach(client => {
                    const option = document.createElement('option');
                    option.value = client.id;
                    option.textContent = client.name;
                    if (currentValue == client.id) {
                        option.selected = true;
                    }
                    select.appendChild(option);
                });
                
                // Nếu chưa có client nào được chọn và có clients, tự động chọn client đầu tiên
                if (!currentValue && clients.length > 0) {
                    select.value = clients[0].id;
                    // Trigger change event để load stream
                    const changeEvent = new Event('change');
                    select.dispatchEvent(changeEvent);
                }
            }
        })
        .catch(error => {
            console.error('Error loading clients for stream selector:', error);
        });
}

function handleDetectionStreamChange(event) {
    const clientId = event.target.value;
    const container = document.getElementById('detection-stream-container');
    
    if (!container) return;
    
    // Stop health check for previous client if any
    const previousClientId = Object.keys(videoStreamStates)[0];
    if (previousClientId) {
        stopVideoStreamHealthCheck(previousClientId);
    }
    
    if (!clientId) {
        container.innerHTML = '<div class="stream-placeholder"><p>Chọn client để xem live stream</p></div>';
        return;
    }
    
    fetch(`/api/clients/${clientId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(client => {
            const processedStreamUrl = `/api/video/stream/processed/${clientId}`;
            
            container.innerHTML = `
                <div class="detection-stream-wrapper">
                    <div class="stream-container" id="detection-stream-${clientId}">
                        <img id="detection-stream-img-${clientId}" 
                             src="${processedStreamUrl}" 
                             alt="Live stream from ${client.name}"
                             onload="handleDetectionStreamLoad(${clientId})"
                             onerror="handleDetectionStreamError(${clientId})">
                    </div>
                    <div class="stream-info">
                        <h4>${client.name}</h4>
                        <p>Status: <span class="${client.is_detect_enabled ? 'status-active' : 'status-inactive'}">${client.is_detect_enabled ? 'Active' : 'Inactive'}</span></p>
                    </div>
                </div>
            `;
        })
        .catch(error => {
            console.error('Error loading client info:', error);
            container.innerHTML = '<div class="stream-placeholder"><p style="color: #e74c3c;">Lỗi khi tải client: ' + error.message + '</p></div>';
        });
}

// Track video stream state for auto-reload
const videoStreamStates = {}; // {clientId: {lastLoadTime, checkInterval, retryCount}}

function handleDetectionStreamLoad(clientId) {
    try {
        // Update last load time
        if (!videoStreamStates[clientId]) {
            videoStreamStates[clientId] = {};
        }
        videoStreamStates[clientId].lastLoadTime = Date.now();
        videoStreamStates[clientId].retryCount = 0;
        
        // Start checking for black screen (no new frames) - silent reload
        startVideoStreamHealthCheck(clientId);
    } catch (error) {
        console.error('Error in handleDetectionStreamLoad:', error);
    }
}

function handleDetectionStreamError(clientId) {
    try {
        // Increment retry count
        if (!videoStreamStates[clientId]) {
            videoStreamStates[clientId] = {};
        }
        videoStreamStates[clientId].retryCount = (videoStreamStates[clientId].retryCount || 0) + 1;
        
        // Silent reconnect after 1 second (nhanh hơn, không hiển thị cảnh báo)
        setTimeout(() => {
            reloadVideoStream(clientId);
        }, 1000);
    } catch (error) {
        console.error('Error in handleDetectionStreamError:', error);
    }
}

function reloadVideoStream(clientId) {
    const img = document.getElementById(`detection-stream-img-${clientId}`);
    if (img) {
        const state = videoStreamStates[clientId] || {};
        const retry = (state.retryCount || 0) + 1;
        img.src = `/api/video/stream/processed/${clientId}?retry=${retry}`;
    }
}

function startVideoStreamHealthCheck(clientId) {
    // Clear existing interval if any
    if (videoStreamStates[clientId] && videoStreamStates[clientId].checkInterval) {
        clearInterval(videoStreamStates[clientId].checkInterval);
    }
    
    // Check every 30 seconds if video is still updating (giảm tần suất reload)
    videoStreamStates[clientId].checkInterval = setInterval(() => {
        checkVideoStreamHealth(clientId);
    }, 30000);
}

function checkVideoStreamHealth(clientId) {
    try {
        const img = document.getElementById(`detection-stream-img-${clientId}`);
        if (!img) {
            // Image element removed, stop checking
            if (videoStreamStates[clientId] && videoStreamStates[clientId].checkInterval) {
                clearInterval(videoStreamStates[clientId].checkInterval);
                delete videoStreamStates[clientId];
            }
            return;
        }
        
        const state = videoStreamStates[clientId];
        if (!state || !state.lastLoadTime) {
            return;
        }
        
        // Check if no new frame loaded in last 45 seconds (video might be black/frozen)
        const timeSinceLastLoad = Date.now() - state.lastLoadTime;
        const maxStaleTime = 45000; // 45 seconds
        
        if (timeSinceLastLoad > maxStaleTime) {
            // Silent reload - không hiển thị cảnh báo, chỉ reload thầm lặng
            reloadVideoStream(clientId);
            
            // Reset last load time
            state.lastLoadTime = Date.now();
        }
    } catch (error) {
        console.error('Error in checkVideoStreamHealth:', error);
    }
}

function stopVideoStreamHealthCheck(clientId) {
    if (videoStreamStates[clientId] && videoStreamStates[clientId].checkInterval) {
        clearInterval(videoStreamStates[clientId].checkInterval);
        delete videoStreamStates[clientId];
    }
}

async function loadClients() {
    try {
        const response = await fetch('/api/clients');
        const clients = await response.json();

        displayClients(clients);
        
        // Update client filter dropdown
        const clientFilter = document.getElementById('client-filter');
        if (clientFilter) {
            const currentValue = clientFilter.value;
            clientFilter.innerHTML = '<option value="">All Clients</option>';
            clients.forEach(client => {
                const option = document.createElement('option');
                option.value = client.id;
                option.textContent = client.name;
                if (currentValue == client.id) {
                    option.selected = true;
                }
                clientFilter.appendChild(option);
            });
        }
        
        return clients; // Return clients for chaining

    } catch (error) {
        console.error('Error loading clients:', error);
        const clientsBody = document.getElementById('clients-body');
        if (clientsBody) {
            clientsBody.innerHTML =
                '<tr><td colspan="6" style="text-align: center; color: #e74c3c;">Error loading clients</td></tr>';
        }
        return []; // Return empty array on error
    }
}

function displayClients(clients) {
    const tbody = document.getElementById('clients-body');

    if (clients.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; color: #7f8c8d;">No clients found</td></tr>';
        return;
    }

    tbody.innerHTML = clients.map(client => {
        const onlineStatus = getOnlineStatus(client.updated_at);
        return `
        <tr>
            <td>${client.serial_number || 'N/A'}</td>
            <td>${client.name}</td>
            <td>
                ${client.latitude && client.longitude ?
            `${client.latitude.toFixed(4)}, ${client.longitude.toFixed(4)}` :
            'Not set'}
            </td>
            <td>
                <span class="status ${client.is_detect_enabled ? 'active' : 'inactive'}">
                    ${client.is_detect_enabled ? 'Enabled' : 'Disabled'}
                </span>
            </td>
            <td>
                <span class="status ${onlineStatus.class}" title="Cập nhật lần cuối: ${client.updated_at ? formatTimestamp(client.updated_at) : 'Never'}">
                    ${onlineStatus.text}
                </span>
            </td>
            <td>${client.client_detections || 0}</td>
            <td>${client.updated_at ? formatTimestamp(client.updated_at) : 'Never'}</td>
            <td>
                <button class="edit-btn" onclick="editClient(${client.id})">Edit</button>
                <button class="delete-btn" onclick="deleteClient(${client.id}, '${client.name}')">Delete</button>
            </td>
        </tr>
    `;
    }).join('');
}

function setupClientModal() {
    const modal = document.getElementById('client-modal');
    const closeBtn = document.getElementById('client-modal-close');

    closeBtn.onclick = function () {
        modal.style.display = 'none';
    };

    window.onclick = function (event) {
        if (event.target == modal) {
            modal.style.display = 'none';
        }
    };
}

function openClientModal(clientId = null) {
    const modal = document.getElementById('client-modal');
    const modalContent = document.getElementById('client-modal-content');

    const isEdit = clientId !== null;
    const title = isEdit ? 'Edit Client' : 'Add New Client';

    modalContent.innerHTML = `
        <h2>${title}</h2>
        <form id="client-form">
            <div class="form-group">
                <label for="client-serial">Serial Number (bắt buộc):</label>
                <input type="text" id="client-serial" placeholder="Ví dụ: 202500000" required ${isEdit ? 'readonly' : ''} style="${isEdit ? 'background: #f5f5f5; cursor: not-allowed;' : ''}">
                <small class="form-help" style="display: block; margin-top: 5px; color: #666;">Format: 2025 + mã nhị phân 5 bit (ví dụ: 202500000, 202500001, ...)</small>
            </div>
            <div class="form-group">
                <label for="client-name">Tên hiển thị:</label>
                <input type="text" id="client-name" placeholder="Ví dụ: Camera 1, Thiết bị A" required>
            </div>
            <div style="display: flex; gap: 12px;">
                <div class="form-group" style="flex: 1;">
                    <label for="client-latitude">Latitude:</label>
                    <input type="number" id="client-latitude" step="0.0001" placeholder="Optional">
                </div>
                <div class="form-group" style="flex: 1;">
                    <label for="client-longitude">Longitude:</label>
                    <input type="number" id="client-longitude" step="0.0001" placeholder="Optional">
                </div>
            </div>

            <div class="form-group" style="margin-top: 12px;">
                <label for="client-ip">Camera local IP Address:</label>
                <input type="text" id="client-ip" placeholder="Ví dụ: 192.168.1.10">
                <small class="form-help" style="display:block;margin-top:6px;color:#6b7280;">Nhập địa chỉ IP của camera. Link RTSP sẽ được client tự ghép từ cấu hình sẵn.</small>
            </div>
            <div class="form-group" style="display:flex; gap:12px;">
                <label class="checkbox-label" style="display:flex; align-items:center; gap:8px;">
                    <input type="checkbox" id="client-show-roi-overlay" checked>
                    Hiển thị ROI trên stream
                </label>
            </div>
            <div class="form-group">
                <label class="checkbox-label">
                    <input type="checkbox" id="client-enabled" checked>
                    Detection Enabled
                </label>
            </div>

            <div class="form-group">
                <label>Region of Interest (ROI) to detect - Nhiều ROI hợp nhất:</label>
                <div class="roi-container">
                    <div class="roi-mode-selector" style="margin-bottom: 10px; display: flex; gap: 15px; align-items: center;">
                        <label style="font-weight: 600;">Chế độ vẽ:</label>
                        <label class="radio-label">
                            <input type="radio" name="roi-draw-mode" value="rectangle" id="roi-mode-rectangle">
                            <span>Hình chữ nhật</span>
                        </label>
                        <label class="radio-label">
                            <input type="radio" name="roi-draw-mode" value="freehand" id="roi-mode-freehand" checked>
                            <span>Vẽ tự do</span>
                        </label>
                    </div>
                    <canvas id="roi-canvas" width="640" height="480"></canvas>
                    <div class="roi-controls">
                        <button type="button" id="capture-frame-btn" class="btn-primary">Chụp ảnh hiện tại</button>
                        <button type="button" id="clear-all-roi-btn" class="btn-secondary">Clear Tất Cả ROI</button>
                        <div class="roi-coords">
                            <label>ROI Count: <span id="roi-count">0</span></label>
                        </div>
                    </div>
                    <div id="roi-list" style="margin-top: 10px; max-height: 150px; overflow-y: auto;"></div>
                </div>
                <small class="form-help" id="roi-help-text">Giữ chuột và kéo tự do trên canvas để vẽ ROI (vẽ tay tự do). Có thể vẽ nhiều ROI - chỉ detect khi object trong TẤT CẢ các ROI. Nhấn "Chụp ảnh hiện tại" để lấy frame từ camera làm nền.</small>
            </div>

            <div class="form-actions">
                <button type="submit" class="btn-primary">${isEdit ? 'Update' : 'Create'} Client</button>
                <button type="button" onclick="document.getElementById('client-modal').style.display='none'">Cancel</button>
            </div>
        </form>
    `;

    const form = document.getElementById('client-form');
    form.onsubmit = function (e) {
        e.preventDefault();
        saveClient(clientId);
    };

    // Clear ROI data when opening modal (important for new clients)
    if (!isEdit) {
        roiRegions = [];
        roiIdCounter = 0;
        // Clear saved image for new client
        if (currentClientId) {
            localStorage.removeItem(`roi_canvas_bg_${currentClientId}`);
        }
    }

    // Initialize ROI canvas
    initROICanvas(clientId);
    
    // Setup ROI draw mode selector
    setTimeout(() => {
        const modeRadios = document.querySelectorAll('input[name="roi-draw-mode"]');
        const helpText = document.getElementById('roi-help-text');
        
        if (modeRadios.length > 0 && helpText) {
            modeRadios.forEach(radio => {
                radio.addEventListener('change', function() {
                    roiDrawMode = this.value;
                    if (roiDrawMode === 'rectangle') {
                        helpText.textContent = 'Click và kéo để vẽ ROI hình chữ nhật. Có thể vẽ nhiều ROI - chỉ detect khi object trong TẤT CẢ các ROI. Nhấn "Chụp ảnh hiện tại" để lấy frame từ camera làm nền.';
                    } else {
                        helpText.textContent = 'Giữ chuột và kéo tự do trên canvas để vẽ ROI (vẽ tay tự do). Có thể vẽ nhiều ROI - chỉ detect khi object trong TẤT CẢ các ROI. Nhấn "Chụp ảnh hiện tại" để lấy frame từ camera làm nền.';
                    }
                });
            });
            
            // Set initial mode
            const initialMode = document.querySelector('input[name="roi-draw-mode"]:checked');
            if (initialMode) {
                roiDrawMode = initialMode.value;
            }
        }
    }, 100);

    // Load client data if editing
    if (isEdit) {
        loadClientForEdit(clientId);
    } else {
        // For new client, clear serial number field and ensure ROI list is updated
        document.getElementById('client-serial').value = '';
        updateROIList();
    }

    modal.style.display = 'block';
}

async function loadClientForEdit(clientId) {
    try {
        const response = await fetch(`/api/clients/${clientId}`);
        const client = await response.json();
        document.getElementById('client-serial').value = client.serial_number || '';
        document.getElementById('client-name').value = client.name;
        document.getElementById('client-latitude').value = client.latitude || '';
        document.getElementById('client-longitude').value = client.longitude || '';
        document.getElementById('client-ip').value = client.ip_address || '';
        const showRoiCheckbox = document.getElementById('client-show-roi-overlay');
        if (showRoiCheckbox) {
            showRoiCheckbox.checked = client.show_roi_overlay !== false;
        }
        document.getElementById('client-enabled').checked = client.is_detect_enabled;

        // Load ROI regions (multiple ROI support)
        roiRegions = [];
        roiIdCounter = 0;
        
        if (client.roi_regions) {
            try {
                const regions = JSON.parse(client.roi_regions);
                if (Array.isArray(regions)) {
                    roiRegions = regions.map((roi, idx) => {
                        // Support both polygon format (points) and rectangle format (x1, y1, x2, y2)
                        if (roi.points && Array.isArray(roi.points)) {
                            // Check if ROI is normalized (0-1)
                            const is_normalized = roi._normalized || false;
                            
                            // Get reference size để scale từ normalized về canvas size
                            const refWidth = roi._ref_width || (canvasBGImage && canvasBGImage.naturalWidth > 0 ? canvasBGImage.naturalWidth : roiCanvas.width);
                            const refHeight = roi._ref_height || (canvasBGImage && canvasBGImage.naturalHeight > 0 ? canvasBGImage.naturalHeight : roiCanvas.height);
                            
                            // Scale points từ normalized về canvas size nếu đã normalize
                            let displayPoints = roi.points;
                            if (is_normalized) {
                                displayPoints = roi.points.map(p => ({
                                    x: p.x * refWidth,
                                    y: p.y * refHeight
                                }));
                            }
                            
                            return {
                                id: roiIdCounter++,
                                name: roi.name || `ROI ${idx + 1}`,
                                color: roi.color || '#e74c3c',
                                colorRgb: roi.colorRgb || [231, 76, 60],
                                points: displayPoints  // Scale về canvas size để hiển thị
                            };
                        } else if (roi.x1 !== undefined && roi.x2 !== undefined) {
                            // Old rectangle format - convert to polygon (4 corners)
                            // Check if normalized
                            const is_normalized = roi._normalized || false;
                            const refWidth = roi._ref_width || (canvasBGImage && canvasBGImage.naturalWidth > 0 ? canvasBGImage.naturalWidth : roiCanvas.width);
                            const refHeight = roi._ref_height || (canvasBGImage && canvasBGImage.naturalHeight > 0 ? canvasBGImage.naturalHeight : roiCanvas.height);
                            
                            let x1 = roi.x1, y1 = roi.y1, x2 = roi.x2, y2 = roi.y2;
                            if (is_normalized) {
                                // Scale from normalized to canvas size
                                x1 = x1 * refWidth;
                                y1 = y1 * refHeight;
                                x2 = x2 * refWidth;
                                y2 = y2 * refHeight;
                            }
                            
                            return {
                                id: roiIdCounter++,
                                name: roi.name || `ROI ${idx + 1}`,
                                color: roi.color || '#e74c3c',
                                colorRgb: roi.colorRgb || [231, 76, 60],
                                points: [
                                    {x: x1, y: y1},
                                    {x: x2, y: y1},
                                    {x: x2, y: y2},
                                    {x: x1, y: y2}
                                ]
                            };
                        }
                        return null;
                    }).filter(roi => roi !== null);
                }
            } catch (e) {
                console.error('Error parsing roi_regions:', e);
            }
        }
        
        // Backward compatibility: Load single ROI if roi_regions is empty
        if (roiRegions.length === 0 && client.roi_x1 && client.roi_y1 && client.roi_x2 && client.roi_y2) {
            roiRegions = [{
                id: roiIdCounter++,
                name: 'ROI 1',
                color: '#e74c3c',
                colorRgb: [231, 76, 60],
                points: [
                    {x: client.roi_x1, y: client.roi_y1},
                    {x: client.roi_x2, y: client.roi_y1},
                    {x: client.roi_x2, y: client.roi_y2},
                    {x: client.roi_x1, y: client.roi_y2}
                ]
            }];
        }
        
        drawCanvasWithImage();
        drawAllROIs();
        updateROIList();

    } catch (error) {
        console.error('Error loading client:', error);
        alert('Error loading client data');
    }
}

async function saveClient(clientId) {
    // Convert ROI regions to JSON string (polygon format)
    // FIX: Normalize ROI coordinates (0-1) để không bị lệch khi resolution thay đổi
    let roiRegionsJson = null;
    if (roiRegions.length > 0) {
        // Get reference size: dùng image natural size nếu có, fallback về canvas size
        const refWidth = (canvasBGImage && canvasBGImage.naturalWidth > 0) ? canvasBGImage.naturalWidth : roiCanvas.width;
        const refHeight = (canvasBGImage && canvasBGImage.naturalHeight > 0) ? canvasBGImage.naturalHeight : roiCanvas.height;
        
        roiRegionsJson = JSON.stringify(roiRegions.map(roi => {
            // Normalize points to 0-1 range dựa trên reference size
            const normalizedPoints = roi.points.map(p => ({
                x: p.x / refWidth,   // Normalize x (0-1)
                y: p.y / refHeight   // Normalize y (0-1)
            }));
            
            return {
                name: roi.name || `ROI ${roiRegions.indexOf(roi) + 1}`,
                color: roi.color || '#e74c3c',
                colorRgb: roi.colorRgb || [231, 76, 60],
                points: normalizedPoints,  // Normalized coordinates (0-1)
                _normalized: true,  // Flag để biết đã normalize
                _ref_width: refWidth,  // Lưu reference width để debug
                _ref_height: refHeight  // Lưu reference height để debug
            };
        }));
    }
    
    // Backward compatibility: Set single ROI if only one ROI exists (calculate bounding box)
    let roi_x1 = null, roi_y1 = null, roi_x2 = null, roi_y2 = null;
    if (roiRegions.length === 1 && roiRegions[0].points) {
        const points = roiRegions[0].points;
        const refWidth = (canvasBGImage && canvasBGImage.naturalWidth > 0) ? canvasBGImage.naturalWidth : roiCanvas.width;
        const refHeight = (canvasBGImage && canvasBGImage.naturalHeight > 0) ? canvasBGImage.naturalHeight : roiCanvas.height;
        // Normalize coordinates
        const xs = points.map(p => p.x / refWidth);
        const ys = points.map(p => p.y / refHeight);
        roi_x1 = Math.min(...xs);
        roi_y1 = Math.min(...ys);
        roi_x2 = Math.max(...xs);
        roi_y2 = Math.max(...ys);
    }
    
    const clientData = {
        serial_number: document.getElementById('client-serial').value.trim(),
        name: document.getElementById('client-name').value.trim(),
        latitude: parseFloat(document.getElementById('client-latitude').value) || null,
        longitude: parseFloat(document.getElementById('client-longitude').value) || null,
        ip_address: document.getElementById('client-ip').value || null,
        show_roi_overlay: document.getElementById('client-show-roi-overlay')?.checked ?? true,
        is_detect_enabled: document.getElementById('client-enabled').checked,
        roi_x1: roi_x1,
        roi_y1: roi_y1,
        roi_x2: roi_x2,
        roi_y2: roi_y2,
        roi_regions: roiRegionsJson  // Multiple ROI regions
    };

    try {
        const url = clientId ? `/api/clients/${clientId}` : '/api/clients';
        const method = clientId ? 'PUT' : 'POST';

        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(clientData)
        });

        if (response.ok) {
            document.getElementById('client-modal').style.display = 'none';
            loadClients();
            loadStats(); // Refresh stats to update client count
            showToastNotification(`Client ${clientId ? 'updated' : 'created'} successfully!`, 'info');
        } else {
            const error = await response.json();
            console.error('Error saving client:', error);
            alert(`Error: ${error.error}`);
        }

    } catch (error) {
        console.error('Error saving client:', error);
        alert('Error saving client');
    }
}

async function deleteClient(clientId, clientName) {
    if (!confirm(`Are you sure you want to delete client "${clientName}"? This action cannot be undone.`)) {
        return;
    }

    try {
        const response = await fetch(`/api/clients/${clientId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            loadClients();
            loadStats(); // Refresh stats
            alert('Client deleted successfully!');
        } else {
            const error = await response.json();
            alert(`Error: ${error.error}`);
        }

    } catch (error) {
        console.error('Error deleting client:', error);
        alert('Error deleting client');
    }
}

function editClient(clientId) {
    openClientModal(clientId);
}

// ROI Canvas functionality - Multiple ROI support (Rectangle or Freehand drawing)
let roiCanvas, roiCtx;
let isDrawing = false;
let currentPath = []; // Array of points for current freehand drawing: [{x, y}, ...]
let startX, startY, endX, endY; // For rectangle drawing
let roiDrawMode = 'freehand'; // 'rectangle' or 'freehand'
let canvasBGImage = new Image();
let roiRegions = []; // Array of ROI polygons: [{id, name, color, points: [{x, y}, ...]}, ...]
// Default ROI colors
const DEFAULT_ROI_COLORS = [
    {name: 'Cyan', value: '#00ffff', rgb: [0, 255, 255]},
    {name: 'Đỏ', value: '#ff0000', rgb: [255, 0, 0]},
    {name: 'Xanh lá', value: '#00ff00', rgb: [0, 255, 0]},
    {name: 'Vàng', value: '#ffff00', rgb: [255, 255, 0]},
    {name: 'Cam', value: '#ff8800', rgb: [255, 136, 0]},
    {name: 'Tím', value: '#ff00ff', rgb: [255, 0, 255]},
    {name: 'Xanh dương', value: '#0000ff', rgb: [0, 0, 255]}
];
let currentClientId = null; // Store current client ID for capturing frame
let roiIdCounter = 0; // Counter for unique ROI IDs
let canvasScaleX = 1.0; // Scale factor for canvas to actual frame
let canvasScaleY = 1.0;

function initROICanvas(clientId) {
    roiCanvas = document.getElementById('roi-canvas');
    roiCtx = roiCanvas.getContext('2d');
    currentClientId = clientId; // Store client ID for capture button

    // Clear canvas
    roiCtx.clearRect(0, 0, roiCanvas.width, roiCanvas.height);

    // Add event listeners
    roiCanvas.addEventListener('mousedown', startDrawing);
    roiCanvas.addEventListener('mousemove', draw);
    roiCanvas.addEventListener('mouseup', stopDrawing);
    roiCanvas.addEventListener('mouseout', stopDrawing);

    // Clear All ROI button
    const clearAllBtn = document.getElementById('clear-all-roi-btn');
    if (clearAllBtn) {
        clearAllBtn.addEventListener('click', clearAllROI);
    }

    // Capture current frame button
    const captureBtn = document.getElementById('capture-frame-btn');
    if (captureBtn) {
        captureBtn.addEventListener('click', captureCurrentFrame);
    }

    // Load last detect image as default background (only if editing existing client)
    if (clientId) {
        getLastDetectImage(clientId);
    } else {
        // For new client, clear canvas and update ROI list
        drawCanvasWithImage();
        updateROIList();
    }
}

async function getLastDetectImage(clientID) {
    try {
        // First, try to load captured image from localStorage
        const savedImage = localStorage.getItem(`roi_canvas_bg_${clientID}`);
        if (savedImage) {
            canvasBGImage.src = savedImage;
            canvasBGImage.onload = () => {
                drawCanvasWithImage();
                drawAllROIs();
                updateROIList();
            };
            return; // Use saved image, don't load from server
        }
        
        // If no saved image, load from server (last detected image)
        let res = await fetch(`/api/clients/${clientID}/last-frame`)
        if (res.ok) {
            let data = await res.json()
            if (data.image) {
                canvasBGImage.src = '/api/images/' + data.image;
                canvasBGImage.onload = () => {
                    drawCanvasWithImage();
                    drawAllROIs();
                    updateROIList();
                }
            }
        }
    } catch (e) {
    }
}

async function captureCurrentFrame() {
    if (!currentClientId) {
        alert('Client ID not found');
        return;
    }
    
    try {
        // Show loading state
        const btn = document.getElementById('capture-frame-btn');
        const originalText = btn.textContent;
        btn.disabled = true;
        btn.textContent = 'Đang chụp...';
        
        // Fetch current frame from stream
        const response = await fetch(`/api/clients/${currentClientId}/current-frame`);
        
        if (response.ok) {
            // Get image as blob
            const blob = await response.blob();
            
            // Convert blob to base64 and save to localStorage
            const reader = new FileReader();
            reader.onload = function() {
                const base64Image = reader.result;
                // Save to localStorage with client ID as key
                localStorage.setItem(`roi_canvas_bg_${currentClientId}`, base64Image);
                
                // Load into canvas background
                canvasBGImage.src = base64Image;
                canvasBGImage.onload = () => {
                    drawCanvasWithImage();
                    // Redraw all ROIs if exist
                    drawAllROIs();
                    updateROIList();
                    btn.disabled = false;
                    btn.textContent = originalText;
                    showToastNotification('Đã chụp ảnh hiện tại từ camera', 'info');
                };
            };
            reader.readAsDataURL(blob);
        } else {
            const error = await response.json();
            alert(`Lỗi: ${error.error || 'Không thể lấy frame hiện tại. Đảm bảo client đang stream video.'}`);
            btn.disabled = false;
            btn.textContent = originalText;
        }
    } catch (error) {
        console.error('Error capturing current frame:', error);
        alert('Lỗi khi chụp ảnh: ' + error.message);
        const btn = document.getElementById('capture-frame-btn');
        btn.disabled = false;
        btn.textContent = 'Chụp ảnh hiện tại';
    }
}

function drawCanvasWithImage() {
    if (!roiCtx || !roiCanvas) return;
    
    // Clear canvas first
    roiCtx.clearRect(0, 0, roiCanvas.width, roiCanvas.height);
    
    // Draw background image if loaded
    if (canvasBGImage.complete && canvasBGImage.naturalWidth > 0) {
        // Scale image to fit canvas while maintaining aspect ratio
        const imgAspect = canvasBGImage.width / canvasBGImage.height;
        const canvasAspect = roiCanvas.width / roiCanvas.height;
        
        let drawWidth, drawHeight, drawX, drawY;
        
        if (imgAspect > canvasAspect) {
            // Image is wider - fit to width
            drawWidth = roiCanvas.width;
            drawHeight = drawWidth / imgAspect;
            drawX = 0;
            drawY = (roiCanvas.height - drawHeight) / 2;
        } else {
            // Image is taller - fit to height
            drawHeight = roiCanvas.height;
            drawWidth = drawHeight * imgAspect;
            drawX = (roiCanvas.width - drawWidth) / 2;
            drawY = 0;
        }
        
        roiCtx.drawImage(canvasBGImage, drawX, drawY, drawWidth, drawHeight);
    }
}

function startDrawing(e) {
    isDrawing = true;
    const rect = roiCanvas.getBoundingClientRect();
    const x = Math.max(0, Math.min(e.clientX - rect.left, roiCanvas.width));
    const y = Math.max(0, Math.min(e.clientY - rect.top, roiCanvas.height));
    
    if (roiDrawMode === 'freehand') {
        // Freehand mode: start path
        currentPath = [];
        currentPath.push({x, y});
    } else {
        // Rectangle mode: store start point
        startX = x;
        startY = y;
        endX = x;
        endY = y;
    }
}

function draw(e) {
    if (!isDrawing) return;

    const rect = roiCanvas.getBoundingClientRect();
    const x = Math.max(0, Math.min(e.clientX - rect.left, roiCanvas.width));
    const y = Math.max(0, Math.min(e.clientY - rect.top, roiCanvas.height));

    // Clear canvas
    drawCanvasWithImage();

    // Get default color for preview
    const defaultColorIndex = roiRegions.length % DEFAULT_ROI_COLORS.length;
    const previewColor = DEFAULT_ROI_COLORS[defaultColorIndex].value;
    
    if (roiDrawMode === 'freehand') {
        // Freehand mode: add point to path and draw
        currentPath.push({x, y});
        
        if (currentPath.length > 1) {
            roiCtx.strokeStyle = previewColor;
            roiCtx.lineWidth = 2;
            roiCtx.beginPath();
            roiCtx.moveTo(currentPath[0].x, currentPath[0].y);
            for (let i = 1; i < currentPath.length; i++) {
                roiCtx.lineTo(currentPath[i].x, currentPath[i].y);
            }
            roiCtx.stroke();
        }
    } else {
        // Rectangle mode: update end point and draw rectangle
        endX = x;
        endY = y;
        
        roiCtx.strokeStyle = previewColor;
        roiCtx.lineWidth = 2;
        const x1 = Math.min(startX, endX);
        const y1 = Math.min(startY, endY);
        const x2 = Math.max(startX, endX);
        const y2 = Math.max(startY, endY);
        roiCtx.strokeRect(x1, y1, x2 - x1, y2 - y1);
    }
    
    // Draw existing ROIs
    drawAllROIs();
}

function stopDrawing(e) {
    if (!isDrawing) return;
    isDrawing = false;

    if (roiDrawMode === 'freehand') {
        // Freehand mode: validate and save polygon
        // Validate path (minimum 3 points to form a polygon)
        if (currentPath.length < 3) {
            // Path too short - just redraw existing ROIs
            drawCanvasWithImage();
            drawAllROIs();
            if (currentPath.length > 0) {
                showToastNotification('ROI quá nhỏ (cần ít nhất 3 điểm)', 'alert');
            }
            currentPath = [];
            return;
        }

        // Calculate bounding box to check minimum size
        const xs = currentPath.map(p => p.x);
        const ys = currentPath.map(p => p.y);
        const minX = Math.min(...xs);
        const maxX = Math.max(...xs);
        const minY = Math.min(...ys);
        const maxY = Math.max(...ys);
        const width = maxX - minX;
        const height = maxY - minY;

        // Validate ROI size (minimum 10x10 pixels)
        if (width >= 10 && height >= 10) {
            // Show modal to enter ROI name and color
            showROIEditModal(currentPath, 'freehand');
        } else {
            // ROI too small
            drawCanvasWithImage();
            drawAllROIs();
            showToastNotification('ROI quá nhỏ (tối thiểu 10x10 pixels)', 'alert');
        }
        
        // Reset current path
        currentPath = [];
    } else {
        // Rectangle mode: validate and save rectangle as polygon
        // Clamp coordinates to canvas bounds
        const clampedStartX = Math.max(0, Math.min(startX, roiCanvas.width));
        const clampedStartY = Math.max(0, Math.min(startY, roiCanvas.height));
        const clampedEndX = Math.max(0, Math.min(endX, roiCanvas.width));
        const clampedEndY = Math.max(0, Math.min(endY, roiCanvas.height));

        // Ensure coordinates are in correct order (x1 < x2, y1 < y2)
        const x1 = Math.min(clampedStartX, clampedEndX);
        const y1 = Math.min(clampedStartY, clampedEndY);
        const x2 = Math.max(clampedStartX, clampedEndX);
        const y2 = Math.max(clampedStartY, clampedEndY);

        // Only add ROI if there's a valid rectangle (not just a point)
        if (x2 > x1 && y2 > y1) {
            // Validate ROI size (minimum 10x10 pixels)
            if ((x2 - x1) >= 10 && (y2 - y1) >= 10) {
                // Convert rectangle to polygon (4 corners)
                const rectPoints = [
                    {x: x1, y: y1},
                    {x: x2, y: y1},
                    {x: x2, y: y2},
                    {x: x1, y: y2}
                ];
                
                // Show modal to enter ROI name and color
                showROIEditModal(rectPoints, 'rectangle');
            } else {
                // ROI too small
                drawCanvasWithImage();
                drawAllROIs();
                showToastNotification('ROI quá nhỏ (tối thiểu 10x10 pixels)', 'alert');
            }
        } else {
            // Invalid rectangle - just redraw existing ROIs
            drawCanvasWithImage();
            drawAllROIs();
        }
    }
}

function drawAllROIs() {
    if (!roiCtx) return;
    
    roiRegions.forEach((roi, idx) => {
        if (!roi.points || roi.points.length < 3) {
            // Backward compatibility: draw rectangle if old format
            if (roi.x1 !== undefined && roi.x2 !== undefined) {
                roiCtx.strokeStyle = '#e74c3c';
                roiCtx.lineWidth = 2;
                roiCtx.strokeRect(roi.x1, roi.y1, roi.x2 - roi.x1, roi.y2 - roi.y1);
                roiCtx.fillStyle = '#e74c3c';
                roiCtx.font = '14px Arial';
                roiCtx.fillText(`ROI ${idx + 1}`, roi.x1 + 5, roi.y1 - 5);
            }
            return;
        }
        
        // Draw polygon with custom color
        const roiColor = roi.color || '#e74c3c';
        roiCtx.strokeStyle = roiColor;
        roiCtx.lineWidth = 2;
        roiCtx.beginPath();
        roiCtx.moveTo(roi.points[0].x, roi.points[0].y);
        for (let i = 1; i < roi.points.length; i++) {
            roiCtx.lineTo(roi.points[i].x, roi.points[i].y);
        }
        roiCtx.closePath();
        roiCtx.stroke();
        
        // Add ROI label (at first point) with custom name
        const labelX = roi.points[0].x;
        const labelY = roi.points[0].y - 5;
        const roiName = roi.name || `ROI ${idx + 1}`;
        roiCtx.fillStyle = roiColor;
        roiCtx.font = 'bold 14px Arial';
        // Draw text with background for better visibility
        const textMetrics = roiCtx.measureText(roiName);
        roiCtx.fillStyle = 'rgba(0, 0, 0, 0.5)';
        roiCtx.fillRect(labelX - 2, labelY - 16, textMetrics.width + 4, 18);
        roiCtx.fillStyle = roiColor;
        roiCtx.fillText(roiName, labelX, labelY);
    });
}

function updateROIList() {
    const roiListDiv = document.getElementById('roi-list');
    if (!roiListDiv) return;
    
    // Update ROI count
    const roiCountSpan = document.getElementById('roi-count');
    if (roiCountSpan) {
        roiCountSpan.textContent = roiRegions.length;
    }
    
    // Clear and rebuild ROI list
    roiListDiv.innerHTML = '';
    
    if (roiRegions.length === 0) {
        roiListDiv.innerHTML = '<p style="color: #999; font-size: 12px;">Chưa có ROI nào. Vẽ ROI trên canvas để thêm.</p>';
        return;
    }
    
    roiRegions.forEach((roi, idx) => {
        const roiItem = document.createElement('div');
        roiItem.className = 'roi-list-item';
        roiItem.style.cssText = 'padding: 8px; margin: 5px 0; background: #f5f5f5; border-radius: 4px; display: flex; justify-content: space-between; align-items: center;';
        
        // Display ROI coordinates
        let coordsText = '';
        if (roi.points && Array.isArray(roi.points) && roi.points.length > 0) {
            // Polygon format - show bounding box
            const xs = roi.points.map(p => p.x);
            const ys = roi.points.map(p => p.y);
            const minX = Math.min(...xs);
            const minY = Math.min(...ys);
            const maxX = Math.max(...xs);
            const maxY = Math.max(...ys);
            coordsText = `Polygon (${roi.points.length} điểm) - BBox: (${Math.floor(minX)}, ${Math.floor(minY)}) → (${Math.floor(maxX)}, ${Math.floor(maxY)})`;
        } else if (roi.x1 !== undefined && roi.x2 !== undefined) {
            // Rectangle format (backward compatibility)
            coordsText = `Rectangle: (${Math.floor(roi.x1)}, ${Math.floor(roi.y1)}) → (${Math.floor(roi.x2)}, ${Math.floor(roi.y2)})`;
        } else {
            coordsText = 'Unknown format';
        }
        
        const roiName = roi.name || `ROI ${idx + 1}`;
        const roiColor = roi.color || '#e74c3c';
        
        roiItem.innerHTML = `
            <div style="display: flex; align-items: center; gap: 10px; flex: 1;">
                <span style="display: inline-block; width: 20px; height: 20px; background: ${roiColor}; border: 1px solid #ddd; border-radius: 3px;"></span>
                <div>
                    <strong>${roiName}</strong>
                    <div style="font-size: 12px; color: #666;">${coordsText}</div>
                </div>
            </div>
            <button type="button" class="btn-remove-roi" data-roi-id="${roi.id}" style="padding: 4px 8px; background: #ef4444; color: white; border: none; border-radius: 4px; cursor: pointer;">Xóa</button>
        `;
        
        // Add click handler for remove button
        const removeBtn = roiItem.querySelector('.btn-remove-roi');
        removeBtn.addEventListener('click', () => removeROI(roi.id));
        
        roiListDiv.appendChild(roiItem);
    });
}

function showROIEditModal(points, mode) {
    // Create modal overlay
    const modalOverlay = document.createElement('div');
    modalOverlay.id = 'roi-edit-modal-overlay';
    modalOverlay.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 10000; display: flex; align-items: center; justify-content: center;';
    
    // Create modal content
    const modalContent = document.createElement('div');
    modalContent.style.cssText = 'background: white; padding: 25px; border-radius: 8px; max-width: 400px; width: 90%; box-shadow: 0 4px 6px rgba(0,0,0,0.1);';
    
    // Get default color (cycle through colors)
    const defaultColorIndex = roiRegions.length % DEFAULT_ROI_COLORS.length;
    const defaultColor = DEFAULT_ROI_COLORS[defaultColorIndex];
    
    modalContent.innerHTML = `
        <h3 style="margin: 0 0 20px 0; color: #333;">Thiết lập ROI</h3>
        <div style="margin-bottom: 15px;">
            <label style="display: block; margin-bottom: 5px; font-weight: 600;">Tên ROI:</label>
            <input type="text" id="roi-name-input" placeholder="Ví dụ: Vùng vườn, Khu vực cảnh báo..." 
                   style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px;"
                   value="ROI ${roiRegions.length + 1}">
        </div>
        <div style="margin-bottom: 20px;">
            <label style="display: block; margin-bottom: 10px; font-weight: 600;">Màu ROI:</label>
            <div id="roi-color-picker" style="display: flex; gap: 10px; flex-wrap: wrap;">
                ${DEFAULT_ROI_COLORS.map((color, idx) => `
                    <div style="display: flex; align-items: center; gap: 5px;">
                        <input type="radio" name="roi-color" value="${color.value}" id="roi-color-${idx}" 
                               ${idx === defaultColorIndex ? 'checked' : ''}
                               style="width: 20px; height: 20px; cursor: pointer;">
                        <label for="roi-color-${idx}" style="cursor: pointer; display: flex; align-items: center; gap: 5px;">
                            <span style="display: inline-block; width: 30px; height: 30px; background: ${color.value}; border: 2px solid #ddd; border-radius: 4px;"></span>
                            <span>${color.name}</span>
                        </label>
                    </div>
                `).join('')}
            </div>
        </div>
        <div style="display: flex; gap: 10px; justify-content: flex-end;">
            <button id="roi-edit-cancel" style="padding: 8px 16px; background: #ccc; border: none; border-radius: 4px; cursor: pointer;">Hủy</button>
            <button id="roi-edit-save" style="padding: 8px 16px; background: #6366f1; color: white; border: none; border-radius: 4px; cursor: pointer;">Lưu</button>
        </div>
    `;
    
    modalOverlay.appendChild(modalContent);
    document.body.appendChild(modalOverlay);
    
    // Handle save
    document.getElementById('roi-edit-save').addEventListener('click', () => {
        const name = document.getElementById('roi-name-input').value.trim() || `ROI ${roiRegions.length + 1}`;
        const selectedColor = document.querySelector('input[name="roi-color"]:checked').value;
        const colorObj = DEFAULT_ROI_COLORS.find(c => c.value === selectedColor);
        
        // Add ROI with name and color
        roiRegions.push({
            id: roiIdCounter++,
            name: name,
            color: selectedColor,
            colorRgb: colorObj.rgb,
            points: points
        });
        // Remove modal
        document.body.removeChild(modalOverlay);
        
        // Redraw canvas with all ROIs
        drawCanvasWithImage();
        drawAllROIs();
        updateROIList();
    });
    
    // Handle cancel
    document.getElementById('roi-edit-cancel').addEventListener('click', () => {
        document.body.removeChild(modalOverlay);
        // Redraw canvas without the new ROI
        drawCanvasWithImage();
        drawAllROIs();
    });
    
    // Close on overlay click
    modalOverlay.addEventListener('click', (e) => {
        if (e.target === modalOverlay) {
            document.body.removeChild(modalOverlay);
            drawCanvasWithImage();
            drawAllROIs();
        }
    });
}

function removeROI(roiId) {
    roiRegions = roiRegions.filter(roi => roi.id !== roiId);
    drawCanvasWithImage();
    drawAllROIs();
    updateROIList();
            showToastNotification('Đã xóa ROI', 'info');
}

function clearAllROI() {
    if (confirm('Bạn có chắc muốn xóa tất cả ROI?')) {
        roiRegions = [];
        roiIdCounter = 0;
        drawCanvasWithImage();
        updateROIList();
        showToastNotification('Đã xóa tất cả ROI', 'info');
    }
}

// Auto-refresh functionality (optional)
let autoRefreshInterval;

function startAutoRefresh() {
    // Delay auto-refresh để không chạy ngay khi load trang (tránh chậm)
    setTimeout(() => {
        autoRefreshInterval = setInterval(refreshData, 15000); // Refresh every 15 seconds (tăng từ 10s)
    }, 5000); // Đợi 5 giây sau khi load trang mới bắt đầu auto-refresh
}

function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
    }
}

// Start auto-refresh when page loads (với delay)
startAutoRefresh();

// ==================== ALERT SETTINGS ====================

async function loadAlertSettings() {
    try {
        const response = await fetch('/api/alert-settings');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const settings = await response.json();
        
        const emailInput = document.getElementById('alert-email-input');
        const emailCheckbox = document.getElementById('email-enabled-checkbox');
        const statusSpan = document.getElementById('email-status');
        
        if (emailInput) {
            emailInput.value = settings.alert_email || '';
        }
        if (emailCheckbox) {
            emailCheckbox.checked = settings.email_enabled || false;
        }

        if (statusSpan) {
            if (settings.alert_email) {
                if (settings.email_enabled) {
                    statusSpan.textContent = `Đã lưu: ${settings.alert_email} (đang bật)`;
                    statusSpan.style.color = '#2ecc71';
                } else {
                    statusSpan.textContent = `Đã lưu: ${settings.alert_email} (đang tắt)`;
                    statusSpan.style.color = '#f39c12';
                }
            } else {
                statusSpan.textContent = '';
            }
        }
    } catch (error) {
        console.error('Error loading alert settings:', error);
    }
}

async function saveAlertSettings() {
    try {
        const emailInput = document.getElementById('alert-email-input');
        const emailCheckbox = document.getElementById('email-enabled-checkbox');
        
        if (!emailInput || !emailCheckbox) return;
        
        const email = emailInput.value.trim();
        const enabled = emailCheckbox.checked;
        
        if (enabled && !email) {
            alert('Vui lòng nhập email trước khi bật cảnh báo!');
            emailCheckbox.checked = false;
            return;
        }
        
        const response = await fetch('/api/alert-settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                alert_email: email || null,
                email_enabled: enabled
            })
        });
        
        if (response.ok) {
            showToastNotification(
                enabled 
                    ? `Đã bật cảnh báo email đến ${email}`
                    : 'Đã tắt cảnh báo email',
                'info'
            );

            const statusSpan = document.getElementById('email-status');
            if (statusSpan) {
                if (email) {
                    statusSpan.textContent = enabled
                        ? `Đã lưu: ${email} (đang bật)`
                        : `Đã lưu: ${email} (đang tắt)`;
                    statusSpan.style.color = enabled ? '#2ecc71' : '#f39c12';
                } else {
                    statusSpan.textContent = '';
                }
            }
        } else {
            const error = await response.json();
            alert(`Lỗi: ${error.error}`);
        }
    } catch (error) {
        console.error('Error saving alert settings:', error);
        alert('Lỗi khi lưu cấu hình email');
    }
}

async function testEmail() {
    try {
        const emailInput = document.getElementById('alert-email-input');
        const testBtn = document.getElementById('test-email-btn');
        
        if (!emailInput) return;
        
        const email = emailInput.value.trim();
        if (!email) {
            alert('Vui lòng nhập email trước khi test!');
            return;
        }
        
        if (testBtn) {
            testBtn.disabled = true;
            testBtn.textContent = 'Đang gửi...';
        }
        
        const response = await fetch('/api/alert-settings/test', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                email: email
            })
        });
        
        if (response.ok) {
            showToastNotification(`Đã gửi email test đến ${email}.`, 'info');
            alert(`Đã gửi email test đến ${email}. Vui lòng kiểm tra hộp thư (cả Spam).`);
        } else {
            const error = await response.json();
            alert(`Lỗi khi gửi email test: ${error.error || 'Không thể gửi email. Kiểm tra cấu hình SMTP.'}`);
        }
        
    } catch (error) {
        console.error('Error testing email:', error);
        alert(`Lỗi: ${error.message || 'Không thể kết nối đến server'}`);
    } finally {
        const testBtn = document.getElementById('test-email-btn');
        if (testBtn) {
            testBtn.disabled = false;
            testBtn.textContent = 'Test Email';
        }
    }
}

// ==================== ALERT SYSTEM ====================

// Request browser notification permission
async function requestNotificationPermission() {
    if ('Notification' in window && Notification.permission === 'default') {
        try {
            const permission = await Notification.requestPermission();
            notificationPermissionGranted = permission === 'granted';
        } catch (error) {
            console.error('Error requesting notification permission:', error);
        }
    } else if ('Notification' in window && Notification.permission === 'granted') {
        notificationPermissionGranted = true;
    }
}

// Play alert sound using Web Audio API
function playAlertSound() {
    try {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        
        // Create a beep sound (800Hz, 200ms)
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        oscillator.frequency.value = 800;
        oscillator.type = 'sine';
        
        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.2);
        
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.2);
    } catch (error) {
        console.error('Error playing alert sound:', error);
    }
}

// Show toast notification
function showToastNotification(message, type = 'info', detection = null) {
    const toastContainer = document.getElementById('toast-container');
    if (!toastContainer) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div class="toast-icon">${type === 'alert' ? '!' : 'i'}</div>
        <div class="toast-content">
            <div class="toast-message">${message}</div>
            ${detection ? `<div class="toast-details">${detection.class_name} - ${(detection.confidence * 100).toFixed(1)}%</div>` : ''}
        </div>
        <button class="toast-close" onclick="this.parentElement.remove()">&times;</button>
    `;

    toastContainer.appendChild(toast);

    // Auto remove after 5 seconds
    setTimeout(() => {
        if (toast.parentElement) {
            toast.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }
    }, 5000);

    // Animate in
    setTimeout(() => toast.classList.add('show'), 10);
}

// Check and alert for new detections - CHỈ CẢNH BÁO KHI CÓ ROI
async function checkAndAlertNewDetections(count, latestDetection = null) {
    if (count <= 0) return;

    // Get latest detection details if not provided
    if (!latestDetection) {
        try {
            const response = await fetch('/api/detections?limit=1&offset=0');
            const detections = await response.json();
            if (detections.length > 0) {
                latestDetection = detections[0];
            }
        } catch (error) {
            console.error('Error fetching latest detection:', error);
            return;
        }
    }

    // QUAN TRỌNG: Chỉ cảnh báo nếu client có ROI được set
    // Vì nếu có ROI → detection chỉ xảy ra trong ROI
    // Nếu không có ROI → detection ở bất kỳ đâu, không cần cảnh báo đặc biệt
    if (!latestDetection || !latestDetection.client) {
        return; // Không có client info, bỏ qua
    }

    // Fetch client info để check ROI
    let clientHasROI = false;
    try {
        const clientResponse = await fetch(`/api/clients/${latestDetection.client.id}`);
        if (clientResponse.ok) {
            const client = await clientResponse.json();
            // Check xem client có ROI không (tất cả 4 tọa độ phải có giá trị)
            clientHasROI = client.roi_x1 !== null && client.roi_y1 !== null && 
                          client.roi_x2 !== null && client.roi_y2 !== null &&
                          client.roi_x1 !== undefined && client.roi_y1 !== undefined &&
                          client.roi_x2 !== undefined && client.roi_y2 !== undefined;
        }
    } catch (error) {
        console.error('Error fetching client info:', error);
        // Nếu lỗi, không cảnh báo để tránh false positive
        return;
    }

    // CHỈ CẢNH BÁO NẾU CLIENT CÓ ROI
    if (!clientHasROI) {
        return;
    }

    const message = count === 1 
        ? `Phát hiện trong ROI: ${latestDetection?.class_name || 'Object'}`
        : `${count} phát hiện mới trong ROI`;

    // 1. Browser Notification
    if (notificationPermissionGranted && 'Notification' in window) {
        try {
            const notification = new Notification('Cảnh báo ROI', {
                body: latestDetection 
                    ? `${latestDetection.class_name} được phát hiện trong ROI tại ${latestDetection.client?.name || 'Unknown'}`
                    : message,
                icon: '/favicon.ico',
                badge: '/favicon.ico',
                tag: 'roi-detection-alert',
                requireInteraction: false
            });

            notification.onclick = function() {
                window.focus();
                if (latestDetection) {
                    showDetectionDetail(latestDetection.id);
                }
                notification.close();
            };

            // Auto close after 5 seconds
            setTimeout(() => notification.close(), 5000);
        } catch (error) {
            console.error('Error showing browser notification:', error);
        }
    }

    // 2. Sound Alert - ĐÃ BỎ (theo yêu cầu)
    // playAlertSound();

    // 3. Toast Notification
    showToastNotification(
        latestDetection 
            ? `Phát hiện trong ROI: ${latestDetection.class_name}`
            : message,
        'alert',
        latestDetection
    );
}

