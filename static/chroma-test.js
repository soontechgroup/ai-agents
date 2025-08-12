// API 基础配置
const API_BASE_URL = '/api/v1/chroma';
let documentCounter = 1;
let requestLogs = [];

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    initializeTabs();
    initializeEventListeners();
});

// 初始化选项卡切换
function initializeTabs() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const targetTab = button.dataset.tab;
            
            // 切换按钮状态
            tabButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            
            // 切换内容显示
            tabContents.forEach(content => {
                content.classList.remove('active');
                if (content.id === `${targetTab}-tab`) {
                    content.classList.add('active');
                }
            });
        });
    });
}

// 初始化事件监听器
function initializeEventListeners() {
    // Enter键提交搜索
    document.getElementById('search-query').addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            performSearch();
        }
    });
}

// 显示加载动画
function showLoading() {
    document.getElementById('loading-overlay').classList.add('show');
}

// 隐藏加载动画
function hideLoading() {
    document.getElementById('loading-overlay').classList.remove('show');
}

// 显示提示消息
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    toast.classList.add('show');
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// 记录API请求
function logRequest(method, url, requestData, responseData, status) {
    const logEntry = {
        timestamp: new Date().toISOString(),
        method,
        url,
        requestData,
        responseData,
        status
    };
    
    requestLogs.unshift(logEntry);
    updateLogsDisplay();
}

// 更新日志显示
function updateLogsDisplay() {
    const logsContainer = document.getElementById('request-logs');
    if (requestLogs.length === 0) {
        logsContainer.innerHTML = '<p class="info-text">API 请求和响应日志将显示在这里</p>';
        return;
    }
    
    logsContainer.innerHTML = requestLogs.map(log => `
        <div class="log-entry">
            <div class="log-timestamp">${log.timestamp}</div>
            <div>
                <span class="log-method ${log.method}">${log.method}</span>
                <span class="log-url">${log.url}</span>
                <span style="color: ${log.status < 400 ? '#28a745' : '#dc3545'}"> [${log.status}]</span>
            </div>
            ${log.requestData ? `
                <div class="log-request">
                    <strong>Request:</strong>
                    <pre>${JSON.stringify(log.requestData, null, 2)}</pre>
                </div>
            ` : ''}
            <div class="log-response">
                <strong>Response:</strong>
                <pre>${JSON.stringify(log.responseData, null, 2)}</pre>
            </div>
        </div>
    `).join('');
    
    // 自动滚动到最新
    if (document.getElementById('auto-scroll').checked) {
        logsContainer.scrollTop = 0;
    }
}

// 清空日志
function clearLogs() {
    requestLogs = [];
    updateLogsDisplay();
    showToast('日志已清空');
}

// API 请求封装
async function apiRequest(endpoint, method = 'GET', data = null) {
    const url = `${API_BASE_URL}${endpoint}`;
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json',
        }
    };
    
    if (data && method !== 'GET') {
        options.body = JSON.stringify(data);
    }
    
    showLoading();
    
    try {
        const response = await fetch(url, options);
        const responseData = await response.json();
        
        // 记录请求
        logRequest(method, url, data, responseData, response.status);
        
        hideLoading();
        
        if (!response.ok) {
            throw new Error(responseData.message || responseData.detail || 'API请求失败');
        }
        
        return responseData;
    } catch (error) {
        hideLoading();
        throw error;
    }
}

// 集合管理功能
async function createCollection() {
    const collectionName = document.getElementById('create-collection-name').value.trim();
    if (!collectionName) {
        showToast('请输入集合名称', 'warning');
        return;
    }
    
    const metadataText = document.getElementById('create-collection-metadata').value.trim();
    let metadata = null;
    
    if (metadataText) {
        try {
            const parsedMetadata = JSON.parse(metadataText);
            // 确保元数据是对象类型
            if (typeof parsedMetadata !== 'object' || parsedMetadata === null || Array.isArray(parsedMetadata)) {
                showToast('元数据必须是JSON对象，例如: {"description": "测试集合"}', 'error');
                return;
            }
            metadata = parsedMetadata;
        } catch (e) {
            showToast('元数据格式错误，请输入有效的JSON对象', 'error');
            return;
        }
    }
    
    try {
        const response = await apiRequest('/collection/create', 'POST', {
            collection_name: collectionName,
            metadata: metadata
        });
        
        const resultBox = document.getElementById('create-collection-result');
        resultBox.className = 'result-box success';
        resultBox.innerHTML = `<pre>${JSON.stringify(response.data, null, 2)}</pre>`;
        
        showToast(response.message);
        
        // 清空输入框
        document.getElementById('create-collection-name').value = '';
        document.getElementById('create-collection-metadata').value = '';
        
        // 自动刷新集合列表
        await listCollections();
    } catch (error) {
        const resultBox = document.getElementById('create-collection-result');
        resultBox.className = 'result-box error';
        resultBox.textContent = error.message;
        showToast(error.message, 'error');
    }
}

async function listCollections() {
    try {
        const response = await apiRequest('/collection/list', 'POST', {});
        const collections = response.data;
        
        const listContainer = document.getElementById('collections-list');
        if (collections.length === 0) {
            listContainer.innerHTML = '<p class="info-text">暂无集合</p>';
        } else {
            listContainer.innerHTML = collections.map(collection => `
                <div class="collection-card">
                    <div class="collection-name">📁 ${collection.name}</div>
                    <div class="collection-count">文档数量: ${collection.count}</div>
                    ${collection.metadata ? `
                        <div class="collection-metadata">
                            元数据: ${JSON.stringify(collection.metadata)}
                        </div>
                    ` : ''}
                </div>
            `).join('');
        }
        
        showToast(`成功获取 ${collections.length} 个集合`);
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function getCollectionInfo() {
    const collectionName = document.getElementById('collection-name-info').value.trim();
    if (!collectionName) {
        showToast('请输入集合名称', 'warning');
        return;
    }
    
    try {
        const response = await apiRequest('/collection/info', 'POST', {
            collection_name: collectionName
        });
        
        const resultBox = document.getElementById('collection-info-result');
        resultBox.className = 'result-box success';
        resultBox.innerHTML = `<pre>${JSON.stringify(response.data, null, 2)}</pre>`;
        
        showToast(response.message);
    } catch (error) {
        const resultBox = document.getElementById('collection-info-result');
        resultBox.className = 'result-box error';
        resultBox.textContent = error.message;
        showToast(error.message, 'error');
    }
}

async function deleteCollection() {
    const collectionName = document.getElementById('collection-name-delete').value.trim();
    if (!collectionName) {
        showToast('请输入集合名称', 'warning');
        return;
    }
    
    if (!confirm(`确定要删除集合 "${collectionName}" 吗？此操作不可恢复！`)) {
        return;
    }
    
    try {
        const response = await apiRequest('/collection/delete', 'POST', {
            collection_name: collectionName
        });
        
        const resultBox = document.getElementById('collection-delete-result');
        resultBox.className = 'result-box success';
        resultBox.textContent = response.message;
        
        showToast(response.message);
        
        // 清空输入框
        document.getElementById('collection-name-delete').value = '';
    } catch (error) {
        const resultBox = document.getElementById('collection-delete-result');
        resultBox.className = 'result-box error';
        resultBox.textContent = error.message;
        showToast(error.message, 'error');
    }
}

// 文档管理功能
// 测试数据生成器
function generateTestData() {
    // 测试文档内容模板
    const testContents = [
        "人工智能（Artificial Intelligence, AI）是计算机科学的一个分支，致力于创建能够执行通常需要人类智能的任务的系统。",
        "机器学习是人工智能的子领域，使计算机能够从数据中学习并改进其性能，而无需明确编程。",
        "深度学习是机器学习的一个分支，使用多层神经网络来学习数据的复杂模式。",
        "自然语言处理（NLP）使计算机能够理解、解释和生成人类语言。",
        "计算机视觉是AI的一个领域，使机器能够从数字图像或视频中获得高级理解。",
        "强化学习是一种机器学习方法，通过与环境的交互来学习最优行为策略。",
        "向量数据库是专门用于存储和检索高维向量数据的数据库系统，常用于相似性搜索。",
        "Transformer架构彻底改变了NLP领域，成为了GPT和BERT等模型的基础。",
        "知识图谱是一种用图结构存储实体及其关系的知识表示方法。",
        "联邦学习允许在保护数据隐私的同时训练机器学习模型。"
    ];
    
    // 测试元数据模板
    const categories = ["技术", "科学", "教育", "研究", "应用"];
    const authors = ["张三", "李四", "王五", "赵六", "钱七"];
    const types = ["article", "note", "research", "tutorial", "documentation"];
    
    // 获取或设置集合名称
    const collectionNameInput = document.getElementById('add-collection-name');
    if (!collectionNameInput.value) {
        collectionNameInput.value = `test_collection_${Date.now()}`;
    }
    
    // 清空现有文档
    const container = document.getElementById('documents-container');
    container.innerHTML = '';
    documentCounter = 0;
    
    // 随机生成3-5个文档
    const docCount = Math.floor(Math.random() * 3) + 3;
    
    for (let i = 0; i < docCount; i++) {
        documentCounter++;
        const randomContent = testContents[Math.floor(Math.random() * testContents.length)];
        const randomCategory = categories[Math.floor(Math.random() * categories.length)];
        const randomAuthor = authors[Math.floor(Math.random() * authors.length)];
        const randomType = types[Math.floor(Math.random() * types.length)];
        
        const metadata = {
            type: randomType,
            category: randomCategory,
            author: randomAuthor,
            timestamp: new Date().toISOString(),
            index: i + 1,
            tags: `${randomCategory.toLowerCase()},${randomType}`,  // 改为逗号分隔的字符串
            source: "test_generator"
        };
        
        const newDocument = document.createElement('div');
        newDocument.className = 'document-item';
        newDocument.dataset.index = documentCounter;
        newDocument.innerHTML = `
            <h4>文档 ${documentCounter}</h4>
            <div class="form-group">
                <label>文档内容</label>
                <textarea class="document-content">${randomContent}</textarea>
            </div>
            <div class="form-group">
                <label>元数据 (JSON格式，可选)</label>
                <textarea class="document-metadata">${JSON.stringify(metadata, null, 2)}</textarea>
            </div>
        `;
        container.appendChild(newDocument);
    }
    
    showToast(`已生成 ${docCount} 个测试文档`, 'success');
    
    // 滚动到第一个文档
    const firstDoc = container.querySelector('.document-item');
    if (firstDoc) {
        firstDoc.scrollIntoView({ behavior: 'smooth' });
    }
}

function addDocumentField() {
    documentCounter++;
    const container = document.getElementById('documents-container');
    const newDocument = document.createElement('div');
    newDocument.className = 'document-item';
    newDocument.dataset.index = documentCounter;
    newDocument.innerHTML = `
        <h4>文档 ${documentCounter}</h4>
        <div class="form-group">
            <label>文档内容</label>
            <textarea class="document-content" placeholder="输入文档内容"></textarea>
        </div>
        <div class="form-group">
            <label>元数据 (JSON格式，可选)</label>
            <textarea class="document-metadata" placeholder='例如: {"type": "article", "author": "张三"}'></textarea>
        </div>
    `;
    container.appendChild(newDocument);
    
    // 滚动到新添加的文档
    newDocument.scrollIntoView({ behavior: 'smooth' });
}

async function submitDocuments() {
    const collectionName = document.getElementById('add-collection-name').value.trim();
    if (!collectionName) {
        showToast('请输入集合名称', 'warning');
        return;
    }
    
    const documentItems = document.querySelectorAll('.document-item');
    const documents = [];
    
    for (const item of documentItems) {
        const content = item.querySelector('.document-content').value.trim();
        const metadataText = item.querySelector('.document-metadata').value.trim();
        
        if (content) {
            const doc = { content };
            
            if (metadataText) {
                try {
                    const parsedMetadata = JSON.parse(metadataText);
                    // 确保元数据是对象类型，不接受数字、字符串、数组等
                    if (typeof parsedMetadata !== 'object' || parsedMetadata === null || Array.isArray(parsedMetadata)) {
                        showToast(`文档 ${item.dataset.index} 的元数据必须是JSON对象，例如: {"key": "value"}`, 'error');
                        return;
                    }
                    doc.metadata = parsedMetadata;
                } catch (e) {
                    showToast(`文档 ${item.dataset.index} 的元数据格式错误，请输入有效的JSON对象`, 'error');
                    return;
                }
            }
            
            documents.push(doc);
        }
    }
    
    if (documents.length === 0) {
        showToast('请至少输入一个文档内容', 'warning');
        return;
    }
    
    try {
        const response = await apiRequest('/document/add', 'POST', {
            collection_name: collectionName,
            documents: documents
        });
        
        const resultBox = document.getElementById('add-documents-result');
        resultBox.className = 'result-box success';
        resultBox.innerHTML = `<pre>${JSON.stringify(response.data, null, 2)}</pre>`;
        
        showToast(response.message);
        
        // 清空表单
        document.getElementById('add-collection-name').value = '';
        document.getElementById('documents-container').innerHTML = `
            <div class="document-item" data-index="0">
                <h4>文档 1</h4>
                <div class="form-group">
                    <label>文档内容</label>
                    <textarea class="document-content" placeholder="输入文档内容"></textarea>
                </div>
                <div class="form-group">
                    <label>元数据 (JSON格式，可选)</label>
                    <textarea class="document-metadata" placeholder='例如: {"type": "article", "author": "张三"}'></textarea>
                </div>
            </div>
        `;
        documentCounter = 1;
    } catch (error) {
        const resultBox = document.getElementById('add-documents-result');
        resultBox.className = 'result-box error';
        resultBox.textContent = error.message;
        showToast(error.message, 'error');
    }
}

async function deleteDocuments() {
    const collectionName = document.getElementById('delete-doc-collection').value.trim();
    if (!collectionName) {
        showToast('请输入集合名称', 'warning');
        return;
    }
    
    const docIds = document.getElementById('delete-doc-ids').value.trim();
    const whereText = document.getElementById('delete-doc-where').value.trim();
    
    if (!docIds && !whereText) {
        showToast('请提供文档ID或元数据过滤条件', 'warning');
        return;
    }
    
    const requestData = { collection_name: collectionName };
    
    if (docIds) {
        requestData.document_ids = docIds.split(',').map(id => id.trim());
    }
    
    if (whereText) {
        try {
            const parsedWhere = JSON.parse(whereText);
            // 确保过滤条件是对象类型
            if (typeof parsedWhere !== 'object' || parsedWhere === null || Array.isArray(parsedWhere)) {
                showToast('过滤条件必须是JSON对象，例如: {"type": "article"}', 'error');
                return;
            }
            requestData.where = parsedWhere;
        } catch (e) {
            showToast('元数据过滤条件格式错误，请输入有效的JSON对象', 'error');
            return;
        }
    }
    
    if (!confirm('确定要删除这些文档吗？')) {
        return;
    }
    
    try {
        const response = await apiRequest('/document/delete', 'POST', requestData);
        
        const resultBox = document.getElementById('delete-documents-result');
        resultBox.className = 'result-box success';
        resultBox.textContent = response.message;
        
        showToast(response.message);
        
        // 清空输入框
        document.getElementById('delete-doc-collection').value = '';
        document.getElementById('delete-doc-ids').value = '';
        document.getElementById('delete-doc-where').value = '';
    } catch (error) {
        const resultBox = document.getElementById('delete-documents-result');
        resultBox.className = 'result-box error';
        resultBox.textContent = error.message;
        showToast(error.message, 'error');
    }
}

// 向量搜索功能
async function performSearch() {
    const collectionName = document.getElementById('search-collection').value.trim();
    const queryText = document.getElementById('search-query').value.trim();
    const nResults = parseInt(document.getElementById('search-n-results').value);
    const whereText = document.getElementById('search-where').value.trim();
    
    if (!collectionName) {
        showToast('请输入集合名称', 'warning');
        return;
    }
    
    if (!queryText) {
        showToast('请输入查询文本', 'warning');
        return;
    }
    
    const requestData = {
        collection_name: collectionName,
        query_text: queryText,
        n_results: nResults || 10
    };
    
    if (whereText) {
        try {
            const parsedWhere = JSON.parse(whereText);
            // 确保过滤条件是对象类型
            if (typeof parsedWhere !== 'object' || parsedWhere === null || Array.isArray(parsedWhere)) {
                showToast('过滤条件必须是JSON对象，例如: {"type": "article"}', 'error');
                return;
            }
            requestData.where = parsedWhere;
        } catch (e) {
            showToast('元数据过滤条件格式错误，请输入有效的JSON对象', 'error');
            return;
        }
    }
    
    try {
        const response = await apiRequest('/document/query', 'POST', requestData);
        const results = response.data;
        
        const resultsContainer = document.getElementById('search-results');
        
        if (results.documents.length === 0) {
            resultsContainer.innerHTML = '<p class="info-text">未找到匹配的文档</p>';
        } else {
            resultsContainer.innerHTML = results.documents.map((doc, index) => `
                <div class="result-item">
                    <div class="result-header">
                        <span class="result-id">ID: ${doc.id}</span>
                        ${doc.distance !== null ? `
                            <span class="result-distance">相似度: ${(1 - doc.distance).toFixed(4)}</span>
                        ` : ''}
                    </div>
                    <div class="result-content">
                        ${doc.content}
                    </div>
                    ${doc.metadata ? `
                        <div class="result-metadata">
                            元数据: ${JSON.stringify(doc.metadata, null, 2)}
                        </div>
                    ` : ''}
                </div>
            `).join('');
        }
        
        showToast(response.message);
    } catch (error) {
        const resultsContainer = document.getElementById('search-results');
        resultsContainer.innerHTML = `<p class="info-text" style="color: var(--danger-color);">搜索失败: ${error.message}</p>`;
        showToast(error.message, 'error');
    }
}