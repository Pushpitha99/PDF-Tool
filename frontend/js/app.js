const tools = [
    { id: 'merge', title: 'Merge PDF', icon: 'merge', endpoint: '/api/v1/pdf/merge', desc: 'Combine PDFs in the order you want with the easiest PDF merger available.', multi: true, category: 'Organize PDF' },
    { id: 'merge-word', title: 'Merge Word', icon: 'integration_instructions', endpoint: '/api/v1/pdf/merge-word', desc: 'Combine multiple Word documents (.docx) into a single document.', multi: true, category: 'Organize PDF' },
    { id: 'merge-powerpoint', title: 'Merge PowerPoint', icon: 'slideshow', endpoint: '/api/v1/pdf/merge-powerpoint', desc: 'Combine multiple PowerPoint presentations (.pptx) into a single presentation.', multi: true, category: 'Organize PDF' },
    { id: 'merge-excel', title: 'Merge Excel', icon: 'table_chart', endpoint: '/api/v1/pdf/merge-excel', desc: 'Combine multiple Excel workbooks (.xlsx) into a single workbook with all sheets.', multi: true, category: 'Organize PDF' },
    { id: 'split', title: 'Split PDF', icon: 'call_split', endpoint: '/api/v1/pdf/split', desc: 'Separate one page or a whole set for easy conversion into independent PDF files.', multi: false, fields: [{ name: 'page_ranges', type: 'text', label: 'Page Ranges (e.g. 1-3,5)'}], category: 'Organize PDF' },
    { id: 'compress', title: 'Compress PDF', icon: 'compress', endpoint: '/api/v1/pdf/compress', desc: 'Reduce file size while optimizing for maximal PDF quality.', multi: true, fields: [{ name: 'compression_level', type: 'select', label: 'Compression Level', options: [{ value: 'recommended', label: 'Recommended Compression (Good quality, medium size)' }, { value: 'extreme', label: 'Extreme Compression (Lower quality, high compression)' }, { value: 'low', label: 'Low Compression (High quality, lower compression)' }] }], category: 'Optimize PDF' },
    { id: 'pdf-to-word', title: 'PDF to Word', icon: 'description', endpoint: '/api/v1/pdf/pdf-to-word', desc: 'Easily convert your PDF files into easy to edit DOCX documents.', multi: false, category: 'Convert from PDF' },
    { id: 'pdf-to-jpg', title: 'PDF to JPG', icon: 'image', endpoint: '/api/v1/pdf/pdf-to-jpg', desc: 'Convert each PDF page into a JPG or extract all images contained in a PDF.', multi: false, category: 'Convert from PDF' },
    { id: 'jpg-to-pdf', title: 'JPG to PDF', icon: 'picture_as_pdf', endpoint: '/api/v1/pdf/jpg-to-pdf', desc: 'Convert JPG images to PDF in seconds.', multi: true, category: 'Convert to PDF' },
    { id: 'word-to-pdf', title: 'Word to PDF', icon: 'picture_as_pdf', endpoint: '/api/v1/pdf/word-to-pdf', desc: 'Make DOC and DOCX files easy to read by converting them to PDF.', multi: false, category: 'Convert to PDF' },
    { id: 'excel-to-pdf', title: 'Excel to PDF', icon: 'picture_as_pdf', endpoint: '/api/v1/pdf/excel-to-pdf', desc: 'Make EXCEL spreadsheets easy to read by converting them to PDF.', multi: false, category: 'Convert to PDF' },
    { id: 'powerpoint-to-pdf', title: 'PowerPoint to PDF', icon: 'picture_as_pdf', endpoint: '/api/v1/pdf/powerpoint-to-pdf', desc: 'Make PPT and PPTX slideshows easy to view by converting them to PDF.', multi: false, category: 'Convert to PDF' },
    { id: 'add-page-numbers', title: 'Add Page Numbers', icon: '123', endpoint: '/api/v1/pdf/add-page-numbers', desc: 'Add page numbers into PDFs with ease.', multi: false, category: 'Edit PDF' },
    { id: 'watermark', title: 'Watermark PDF', icon: 'branding_watermark', endpoint: '/api/v1/pdf/watermark', desc: 'Stamp an image or text over your PDF in seconds.', multi: false, fields: [{ name: 'watermark_text', type: 'text', label: 'Watermark Text'}], category: 'Edit PDF' },
    { id: 'rotate', title: 'Rotate PDF', icon: 'rotate_right', endpoint: '/api/v1/pdf/rotate', desc: 'Rotate your PDFs the way you need them.', multi: false, fields: [{ name: 'angle', type: 'number', label: 'Rotation Angle (90, 180, 270)'}], category: 'Edit PDF' },
    { id: 'protect', title: 'Protect PDF', icon: 'lock', endpoint: '/api/v1/pdf/protect', desc: 'Encrypt your PDF with a password to keep sensitive data confidential.', multi: false, fields: [{ name: 'password', type: 'password', label: 'Password'}], category: 'PDF Security' },
    { id: 'unlock', title: 'Unlock PDF', icon: 'lock_open', endpoint: '/api/v1/pdf/unlock', desc: 'Remove PDF password security, giving you the freedom to use your PDFs as you want.', multi: false, fields: [{ name: 'password', type: 'password', label: 'Password'}], category: 'PDF Security' },
    { id: 'organize', title: 'Organize PDF', icon: 'reorder', endpoint: '/api/v1/pdf/organize', desc: 'Sort, add and delete PDF pages.', multi: false, fields: [{ name: 'page_order', type: 'text', label: 'Page Order (e.g. 3,1,2)'}], category: 'Organize PDF' },
    { id: 'sign', title: 'Sign PDF', icon: 'draw', endpoint: '/api/v1/pdf/sign', desc: 'Sign yourself or request electronic signatures from others.', multi: false, fields: [{ name: 'signature_image', type: 'file', label: 'Signature Image'}], category: 'PDF Security' },
    { id: 'ocr-text', title: 'OCR to Text', icon: 'text_snippet', endpoint: '/api/v1/pdf/ocr-text', desc: 'Extract text from scanned PDFs or images via OCR.', multi: false, fields: [{ name: 'language', type: 'text', label: 'Language (e.g., eng)'}], category: 'Edit PDF' },
    { id: 'ocr-pdf', title: 'Make Searchable', icon: 'manage_search', endpoint: '/api/v1/pdf/ocr-pdf', desc: 'Make a scanned PDF searchable by overlaying text via OCR.', multi: false, fields: [{ name: 'language', type: 'text', label: 'Language (e.g., eng)'}], category: 'Edit PDF' }
];

let currentTool = null;
let selectedFiles = [];

document.addEventListener('DOMContentLoaded', () => {
    renderToolsGrid();
    setupEventListeners();
});

function renderToolsGrid() {
    const grid = document.getElementById('tools-grid');
    grid.innerHTML = '';
    
    // Group tools by category
    const categorizedTools = {};
    tools.forEach(tool => {
        if (!categorizedTools[tool.category]) categorizedTools[tool.category] = [];
        categorizedTools[tool.category].push(tool);
    });

    // Create sections for each category
    for (const [category, categoryTools] of Object.entries(categorizedTools)) {
        const categorySection = document.createElement('div');
        categorySection.className = 'category-section';
        categorySection.innerHTML = `<h2 class="category-title">${category}</h2>`;
        
        const categoryGrid = document.createElement('div');
        categoryGrid.className = 'category-grid';

        categoryTools.forEach(tool => {
            const card = document.createElement('div');
            card.className = 'tool-card';
            
            card.onclick = () => openWorkspace(tool);
            
            card.innerHTML = `
                <span class="material-symbols-rounded tool-icon">${tool.icon}</span>
                <h3>${tool.title}</h3>
                <p>${tool.desc}</p>
            `;
            categoryGrid.appendChild(card);
        });

        categorySection.appendChild(categoryGrid);
        grid.appendChild(categorySection);
    }
}

function openWorkspace(tool) {
    currentTool = tool;
    selectedFiles = [];
    
    document.getElementById('main-view').classList.add('hidden');
    document.getElementById('workspace-view').classList.remove('hidden');
    document.body.classList.add('tool-active');
    
    document.getElementById('workspace-title').textContent = tool.title;
    document.getElementById('workspace-desc').textContent = tool.desc;
    document.getElementById('breadcrumb-category').textContent = tool.category;
    document.getElementById('breadcrumb-current').textContent = tool.title;
    document.getElementById('btn-execute-text').textContent = tool.title;
    
    // Reset file input
    const fileInput = document.getElementById('file-input');
    fileInput.multiple = tool.multi;
    if (tool.id.includes('jpg')) {
        fileInput.accept = "image/jpeg, image/png";
    } else if (tool.id === 'word-to-pdf' || tool.id === 'merge-word') {
        fileInput.accept = ".doc,.docx";
    } else if (tool.id === 'excel-to-pdf' || tool.id === 'merge-excel') {
        fileInput.accept = ".xls,.xlsx";
    } else if (tool.id === 'powerpoint-to-pdf' || tool.id === 'merge-powerpoint') {
        fileInput.accept = ".ppt,.pptx";
    } else {
        fileInput.accept = ".pdf";
    }
    fileInput.value = '';
    
    updateFileList();
    resetOverlays();
    
    // Render dynamic inputs
    const dynamicInputs = document.getElementById('dynamic-inputs');
    dynamicInputs.innerHTML = '';
    
    if (tool.fields) {
        tool.fields.forEach(field => {
            const group = document.createElement('div');
            group.className = 'input-group';
            
            const label = document.createElement('label');
            label.textContent = field.label;
            label.htmlFor = `input-${field.name}`;
            group.appendChild(label);
            
            if (field.type === 'select') {
                const select = document.createElement('select');
                select.id = `input-${field.name}`;
                select.name = field.name;
                select.className = 'form-control';
                select.style.width = '100%';
                select.style.padding = '0.6rem 0.8rem';
                select.style.borderRadius = '6px';
                select.style.border = '1px solid #ccc';
                select.style.fontSize = '14px';
                
                field.options.forEach(opt => {
                    const option = document.createElement('option');
                    option.value = opt.value;
                    option.textContent = opt.label;
                    select.appendChild(option);
                });
                group.appendChild(select);
            } else {
                const input = document.createElement('input');
                input.type = field.type;
                input.id = `input-${field.name}`;
                input.name = field.name;
                input.required = true;
                
                if (field.type === 'file') {
                    input.accept = "image/*";
                }
                group.appendChild(input);
            }
            
            dynamicInputs.appendChild(group);
        });
    }
}

function setupEventListeners() {
    // Mobile Menu Toggle
    const mobileMenuBtn = document.getElementById('mobile-menu-toggle');
    if (mobileMenuBtn) {
        mobileMenuBtn.addEventListener('click', () => {
            document.getElementById('main-nav').classList.toggle('active');
        });
    }

    // Mobile Dropdown Toggle (for links with dropdowns)
    const dropdownBtns = document.querySelectorAll('.dropbtn');
    dropdownBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            if (window.innerWidth <= 768) {
                e.preventDefault();
                const dropdown = btn.closest('.dropdown');
                dropdown.classList.toggle('active');
            }
        });
    });

    const returnToHome = (e) => {
        if(e) e.preventDefault();
        document.getElementById('workspace-view').classList.add('hidden');
        document.getElementById('main-view').classList.remove('hidden');
        document.body.classList.remove('tool-active');
    };

    // Home / Exit buttons
    document.getElementById('btn-back').addEventListener('click', returnToHome);
    
    // Clear all files
    document.getElementById('btn-clear-all').addEventListener('click', () => {
        selectedFiles = [];
        updateFileList();
    });
    
    // Logo click
    document.querySelector('.logo').addEventListener('click', (e) => {
        e.preventDefault();
        document.getElementById('workspace-view').classList.add('hidden');
        document.getElementById('main-view').classList.remove('hidden');
    });
    
    // File input change
    document.getElementById('file-input').addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });
    
    // Dropzone Drag & Drop
    const dropzone = document.getElementById('dropzone');
    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('dragover');
    });
    
    dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('dragover');
    });
    
    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
    });
    
    // Execute action
    document.getElementById('btn-execute').addEventListener('click', executeTool);
    
    // Overlays actions
    document.getElementById('btn-restart').addEventListener('click', () => openWorkspace(currentTool));
    document.getElementById('btn-error-back').addEventListener('click', resetOverlays);
}

function handleFiles(files) {
    if (!files || files.length === 0) return;
    
    if (currentTool.multi) {
        selectedFiles = [...selectedFiles, ...Array.from(files)];
    } else {
        selectedFiles = [files[0]];
    }
    
    updateFileList();
    
    // Show settings panel if files are selected
    if (selectedFiles.length > 0) {
        document.getElementById('settings-panel').classList.remove('hidden');
    }
}

function updateFileList() {
    const list = document.getElementById('file-list');
    const container = document.getElementById('file-list-container');
    list.innerHTML = '';
    
    if (selectedFiles.length === 0) {
        container.classList.add('hidden');
        document.getElementById('settings-panel').classList.add('hidden');
        return;
    }
    
    container.classList.remove('hidden');
    selectedFiles.forEach((file, index) => {
        const item = document.createElement('div');
        item.className = 'file-item';
        item.innerHTML = `
            <span><span class="material-symbols-rounded" style="font-size:16px; vertical-align:middle; margin-right:5px;">insert_drive_file</span>${file.name}</span>
            <span class="material-symbols-rounded" style="cursor:pointer; color:#F44336" onclick="removeFile(${index})">close</span>
        `;
        list.appendChild(item);
    });
}

window.removeFile = function(index) {
    selectedFiles.splice(index, 1);
    updateFileList();
};

function resetOverlays() {
    document.getElementById('loading-overlay').classList.add('hidden');
    document.getElementById('success-overlay').classList.add('hidden');
    document.getElementById('error-overlay').classList.add('hidden');
}

async function executeTool() {
    if (selectedFiles.length === 0) return;
    
    const formData = new FormData();
    
    // Add files
    let totalSize = 0;
    if (currentTool.multi) {
        selectedFiles.forEach(f => {
            formData.append('files', f);
            totalSize += f.size;
        });
    } else {
        formData.append('file', selectedFiles[0]);
        totalSize += selectedFiles[0].size;
    }
    
    // 50MB limit
    if (totalSize > 50 * 1024 * 1024) {
        showError("File size exceeds the 50MB limit. Please select smaller files.");
        return;
    }
    
    // Add dynamic fields
    if (currentTool.fields) {
        for (const field of currentTool.fields) {
            const input = document.getElementById(`input-${field.name}`);
            if (field.type === 'file') {
                if (input.files.length > 0) {
                    formData.append(field.name, input.files[0]);
                } else {
                    showError(`Please provide ${field.label}`);
                    return;
                }
            } else {
                if (!input.value) {
                    showError(`Please provide ${field.label}`);
                    input.focus();
                    return;
                }
                formData.append(field.name, input.value);
            }
        }
    }
    
    const executeBtn = document.getElementById('btn-execute');
    executeBtn.disabled = true;
    executeBtn.style.opacity = '0.5';
    executeBtn.style.cursor = 'not-allowed';
    
    document.getElementById('loading-overlay').classList.remove('hidden');
    
    try {
        const response = await fetch(currentTool.endpoint, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            let errText = "Unknown error occurred on server.";
            try {
                const contentType = response.headers.get("content-type");
                if (contentType && contentType.includes("application/json")) {
                    const errData = await response.json();
                    errText = errData.detail || JSON.stringify(errData);
                } else {
                    errText = await response.text();
                }
            } catch (e) {
                errText = response.statusText || errText;
            }
            throw new Error(errText);
        }
        
        // Handle file download
        const blob = await response.blob();
        const contentDisposition = response.headers.get('content-disposition');
        let filename = `${currentTool.id}_result`;
        if (contentDisposition) {
            const match = contentDisposition.match(/filename="(.+)"/);
            if (match) filename = match[1];
        } else if (blob.type === 'application/zip') {
            filename += '.zip';
        } else if (blob.type.includes('wordprocessingml') || blob.type.includes('word')) {
            filename += '.docx';
        } else if (blob.type.includes('presentationml') || blob.type.includes('presentation')) {
            filename += '.pptx';
        } else if (blob.type.includes('spreadsheetml') || blob.type.includes('excel') || blob.type.includes('spreadsheet')) {
            filename += '.xlsx';
        } else if (blob.type === 'text/plain') {
            filename += '.txt';
        } else {
            filename += '.pdf';
        }
        
        const url = window.URL.createObjectURL(blob);
        const downloadBtn = document.getElementById('btn-download');
        downloadBtn.onclick = () => {
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        };
        
        document.getElementById('success-overlay').classList.remove('hidden');
        
    } catch (error) {
        console.error("Tool execution error:", error);
        const msg = error.message || "An unexpected error occurred during file processing.";
        alert("Operation Failed: " + msg);
        showError(msg);
    } finally {
        // ALWAYS hide loading spinner/overlay regardless of success or failure
        document.getElementById('loading-overlay').classList.add('hidden');
        executeBtn.disabled = false;
        executeBtn.style.opacity = '1';
        executeBtn.style.cursor = 'pointer';
    }
}

function showError(msg) {
    document.getElementById('loading-overlay').classList.add('hidden');
    document.getElementById('error-message').textContent = msg;
    document.getElementById('error-overlay').classList.remove('hidden');
}

window.navigateToTool = function(toolId) {
    const tool = tools.find(t => t.id === toolId);
    if (tool) {
        openWorkspace(tool);
    }
};
