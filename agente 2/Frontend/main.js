const API_URL = '/api';

const elements = {
    explorerSection: document.getElementById('explorer-section'),
    breadcrumb: document.getElementById('breadcrumb'),
    fileGrid: document.getElementById('file-grid'),
    btnProcessCurrent: document.getElementById('btn-process-current'),
    
    resultsContainer: document.getElementById('results-container'),
    courseName: document.getElementById('course-name'),
    destId: document.getElementById('dest-id'),
    resultsBody: document.getElementById('results-body'),
    resultsCount: document.getElementById('results-count'),
    btnCancel: document.getElementById('btn-cancel'),
    btnRun: document.getElementById('btn-run'),
    
    toast: document.getElementById('toast'),
    loading: document.getElementById('loading')
};

// SVG Icons
const iconFolder = `<svg class="icon" width="24" height="24" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"></path></svg>`;
const iconFile = `<svg class="icon" width="24" height="24" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"></path></svg>`;
const iconDownload = `<svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>`;

let navHistory = [{ id: 'root', name: 'Meu Drive' }];
let currentFolderId = 'root';
let previewData = null;

window.downloadFile = (fileId) => {
    window.open(`${API_URL}/download/${fileId}`, '_blank');
};

function showToast(message, type = 'info') {
    elements.toast.textContent = message;
    elements.toast.className = `toast show ${type}`;
    setTimeout(() => { elements.toast.className = 'toast'; }, 4000);
}

function setLoading(isLoading) {
    elements.loading.style.display = isLoading ? 'flex' : 'none';
}

function renderBreadcrumb() {
    elements.breadcrumb.innerHTML = '';
    navHistory.forEach((item, index) => {
        const span = document.createElement('span');
        span.className = index === navHistory.length - 1 ? 'crumb active' : 'crumb';
        span.textContent = item.name;
        span.onclick = () => navigateToHistoryIndex(index);
        
        elements.breadcrumb.appendChild(span);
        
        if (index < navHistory.length - 1) {
            const separator = document.createElement('span');
            separator.className = 'crumb-separator';
            separator.textContent = '>';
            elements.breadcrumb.appendChild(separator);
        }
    });
}

function navigateToHistoryIndex(index) {
    navHistory = navHistory.slice(0, index + 1);
    const targetFolder = navHistory[navHistory.length - 1];
    loadFolder(targetFolder.id);
}

async function loadFolder(folderId) {
    currentFolderId = folderId;
    elements.fileGrid.innerHTML = `<div class="grid-loading">Carregando itens...</div>`;
    renderBreadcrumb();
    
    try {
        const response = await fetch(`${API_URL}/drive/${folderId}`);
        const result = await response.json();
        
        if (!response.ok) throw new Error(result.error || 'Erro ao carregar pasta');
        
        renderFileGrid(result.data);
    } catch (error) {
        showToast(error.message, 'error');
        elements.fileGrid.innerHTML = `<div class="grid-loading" style="color:var(--danger)">Erro ao carregar.</div>`;
    }
}

function renderFileGrid(items) {
    elements.fileGrid.innerHTML = '';
    
    if (items.length === 0) {
        elements.fileGrid.innerHTML = `<div class="grid-loading">Esta pasta está vazia.</div>`;
        return;
    }
    
    items.forEach(item => {
        const div = document.createElement('div');
        div.className = `file-item ${item.is_folder ? 'folder' : 'file'}`;
        div.title = item.name;
        div.innerHTML = `
            ${item.is_folder ? iconFolder : iconFile}
            <span class="name">${item.name}</span>
            ${!item.is_folder ? `<button class="btn-download" onclick="event.stopPropagation(); downloadFile('${item.id}')" title="Baixar Arquivo">${iconDownload}</button>` : ''}
        `;
        
        if (item.is_folder) {
            div.onclick = () => {
                navHistory.push({ id: item.id, name: item.name });
                loadFolder(item.id);
            };
        }
        
        elements.fileGrid.appendChild(div);
    });
}

// Inicializar
loadFolder('root');

// ---- Actions ----

elements.btnProcessCurrent.addEventListener('click', async () => {
    if (currentFolderId === 'root') {
        showToast('Não é possível processar a raiz. Entre na pasta do curso.', 'error');
        return;
    }
    
    setLoading(true);
    
    try {
        // Obter nome sugerido (nome da pasta atual)
        const currentFolderName = navHistory[navHistory.length - 1].name;
        
        const response = await fetch(`${API_URL}/preview`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                source_id: currentFolderId,
                course_name: currentFolderName
            })
        });

        const result = await response.json();
        if (!response.ok) throw new Error(result.error || 'Erro desconhecido');

        previewData = result.data;
        elements.courseName.value = currentFolderName;
        
        renderResultsTable(previewData);
        
        // Trocar telas
        elements.explorerSection.style.display = 'none';
        elements.resultsContainer.style.display = 'block';
        showToast('Pré-visualização carregada com sucesso!', 'success');

    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        setLoading(false);
    }
});

function renderResultsTable(data) {
    elements.resultsBody.innerHTML = '';
    
    if (data.length === 0) {
        elements.resultsBody.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--text-secondary)">Nenhum arquivo válido encontrado</td></tr>`;
        elements.btnRun.disabled = true;
    } else {
        data.forEach(item => {
            const tr = document.createElement('tr');
            const pathHtml = item.path_list.map(p => `<span class="path-badge">${p}</span>`).join(' &gt; ');
            tr.innerHTML = `
                <td style="font-weight: 500">${item.file_name}</td>
                <td>${pathHtml}</td>
                <td>${item.categoria} <br><small style="color:var(--text-secondary)">${item.modalidade}</small></td>
                <td>${item.ano_semestre || '-'}</td>
            `;
            elements.resultsBody.appendChild(tr);
        });
        elements.btnRun.disabled = false;
    }
    
    elements.resultsCount.textContent = `${data.length} arquivos`;
}

elements.btnCancel.addEventListener('click', () => {
    elements.resultsContainer.style.display = 'none';
    elements.explorerSection.style.display = 'block';
    previewData = null;
});

elements.btnRun.addEventListener('click', async () => {
    if (!previewData || previewData.length === 0) return;
    
    if (!confirm(`Deseja realmente copiar e organizar ${previewData.length} arquivos no Drive?`)) return;

    setLoading(true);

    try {
        const destId = elements.destId.value.trim();
        const courseName = elements.courseName.value.trim();
        
        const response = await fetch(`${API_URL}/run`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                source_id: currentFolderId,
                dest_id: destId || undefined,
                course_name: courseName || undefined
            })
        });

        const result = await response.json();
        if (!response.ok) throw new Error(result.error || 'Erro durante a automação');

        showToast(result.message, 'success');
        elements.btnRun.disabled = true;
        
        // Voltar pro navegador após sucesso
        setTimeout(() => {
            elements.btnCancel.click();
        }, 3000);

    } catch (error) {
        showToast(error.message, 'error');
    } finally {
        setLoading(false);
    }
});
