// API 基础配置
// 本地测试用，直接写死后端地址
const API_BASE_URL = 'http://localhost:8000/api/v1/chroma';
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
        
        // 构建更丰富的结果展示
        let resultHTML = '<div class="add-result-container">';
        
        // 基本信息
        resultHTML += `
            <div class="result-section">
                <h4><i class="fas fa-info-circle"></i> 基本信息</h4>
                <div class="info-grid">
                    <div class="info-item">
                        <span class="info-label">集合名称:</span>
                        <span class="info-value">${response.data.collection_name}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">添加数量:</span>
                        <span class="info-value">${response.data.added_count} 个文档</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">文档ID:</span>
                        <span class="info-value">${response.data.document_ids.slice(0, 3).join(', ')}${response.data.document_ids.length > 3 ? '...' : ''}</span>
                    </div>
                </div>
            </div>
        `;
        
        // 向量信息
        if (response.data.sample_embeddings && response.data.sample_embeddings.length > 0) {
            const embeddings = response.data.sample_embeddings;
            const embeddingDimension = embeddings[0].length;
            
            resultHTML += `
                <div class="result-section">
                    <h4><i class="fas fa-project-diagram"></i> 向量信息</h4>
                    <div class="vector-info">
                        <div class="info-item">
                            <span class="info-label">向量模型:</span>
                            <span class="info-value">text-embedding-3-small (OpenAI)</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">向量维度:</span>
                            <span class="info-value">${embeddingDimension} 维</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">展示样例:</span>
                            <span class="info-value">前 ${embeddings.length} 个文档的向量</span>
                        </div>
                    </div>
                    
                    <div class="embeddings-preview">
                        <h5>向量预览（前10个维度）</h5>
                        <div class="embeddings-table">
                            ${embeddings.map((embedding, idx) => `
                                <div class="embedding-row">
                                    <div class="doc-label">文档 ${idx + 1}:</div>
                                    <div class="embedding-values">
                                        ${embedding.slice(0, 10).map(val => `<span class="embedding-val">${val.toFixed(4)}</span>`).join('')}
                                        <span class="embedding-more">... +${embeddingDimension - 10} 更多维度</span>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                </div>
            `;
        }
        
        // 原始数据（折叠显示）
        resultHTML += `
            <details class="raw-data-details">
                <summary><i class="fas fa-code"></i> 查看原始响应数据</summary>
                <pre>${JSON.stringify(response.data, null, 2)}</pre>
            </details>
        `;
        
        resultHTML += '</div>';
        resultBox.innerHTML = resultHTML;
        
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
            // 添加向量搜索统计信息
            let searchHTML = `
                <div class="search-stats">
                    <div class="stat-item">
                        <i class="fas fa-chart-line"></i>
                        <span>找到 <strong>${results.total_results}</strong> 个相关文档</span>
                    </div>
                    <div class="stat-item">
                        <i class="fas fa-robot"></i>
                        <span>向量模型: <strong>text-embedding-3-small</strong></span>
                    </div>
                    <div class="stat-item">
                        <i class="fas fa-cube"></i>
                        <span>向量维度: <strong>1536</strong> 维</span>
                    </div>
                </div>
            `;
            
            searchHTML += results.documents.map((doc, index) => {
                // 计算相似度百分比和相似度等级
                const similarity = doc.distance !== null ? (1 - doc.distance) : 0;
                const similarityPercent = (similarity * 100).toFixed(1);
                let similarityClass = 'low';
                let similarityLabel = '低';
                
                if (similarity > 0.9) {
                    similarityClass = 'very-high';
                    similarityLabel = '极高';
                } else if (similarity > 0.8) {
                    similarityClass = 'high';
                    similarityLabel = '高';
                } else if (similarity > 0.7) {
                    similarityClass = 'medium';
                    similarityLabel = '中';
                } else if (similarity > 0.5) {
                    similarityClass = 'low-medium';
                    similarityLabel = '中低';
                }
                
                return `
                    <div class="result-item rank-${index + 1}">
                        <div class="result-header">
                            <div class="result-rank">#${index + 1}</div>
                            <div class="result-similarity similarity-${similarityClass}">
                                <div class="similarity-bar">
                                    <div class="similarity-fill" style="width: ${similarityPercent}%"></div>
                                </div>
                                <div class="similarity-text">
                                    <span class="similarity-percent">${similarityPercent}%</span>
                                    <span class="similarity-label">${similarityLabel}</span>
                                </div>
                            </div>
                        </div>
                        <div class="result-body">
                            <div class="result-content">
                                <i class="fas fa-file-alt"></i>
                                ${doc.content}
                            </div>
                            ${doc.metadata ? `
                                <div class="result-metadata">
                                    <details>
                                        <summary><i class="fas fa-tags"></i> 元数据</summary>
                                        <pre>${JSON.stringify(doc.metadata, null, 2)}</pre>
                                    </details>
                                </div>
                            ` : ''}
                            <div class="result-footer">
                                <span class="result-id"><i class="fas fa-fingerprint"></i> ${doc.id.substring(0, 8)}...</span>
                                ${doc.distance !== null ? `
                                    <span class="result-distance"><i class="fas fa-ruler"></i> 距离: ${doc.distance.toFixed(6)}</span>
                                ` : ''}
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
            
            resultsContainer.innerHTML = searchHTML;
        }
        
        showToast(response.message);
    } catch (error) {
        const resultsContainer = document.getElementById('search-results');
        resultsContainer.innerHTML = `<p class="info-text" style="color: var(--danger-color);">搜索失败: ${error.message}</p>`;
        showToast(error.message, 'error');
    }
}