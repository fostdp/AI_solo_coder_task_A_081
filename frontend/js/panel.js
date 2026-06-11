class PanelManager {
    constructor(panelSelector) {
        this.panel = document.querySelector(panelSelector);
        this.content = this.panel.querySelector('#panel-content');
        this.isVisible = false;
        
        this.setupCloseButton();
    }
    
    setupCloseButton() {
        const closeBtn = this.panel.querySelector('#close-panel');
        closeBtn.addEventListener('click', () => {
            this.hide();
        });
    }
    
    show() {
        this.panel.style.display = 'block';
        this.isVisible = true;
    }
    
    hide() {
        this.panel.style.display = 'none';
        this.isVisible = false;
    }
    
    setContent(html) {
        this.content.innerHTML = html;
    }
    
    showNodeDetail(node) {
        this.show();
        
        if (node.type === 'herb') {
            this.showHerbDetail(node);
        } else if (node.type === 'formula') {
            this.showFormulaDetail(node);
        } else if (node.type === 'disease') {
            this.showDiseaseDetail(node);
        }
    }
    
    showHerbDetail(node) {
        const props = node.properties || {};
        const nature = props.nature || '';
        const natureClass = this.getNatureClass(nature);
        
        const html = `
            <h3>${node.label}</h3>
            
            <div class="panel-section">
                <h4>基本信息</h4>
                <div class="info-item">
                    <span class="info-label">类别</span>
                    <span class="info-value">${props.category || '-'}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">药性</span>
                    <span class="info-value">
                        <span class="tag ${natureClass}">${nature || '-'}</span>
                    </span>
                </div>
            </div>
            
            <div class="panel-section">
                <h4>药味</h4>
                <div class="tag-list">
                    ${(props.flavor || []).map(f => `<span class="tag">${f}</span>`).join('') || '<span style="color:#999">暂无</span>'}
                </div>
            </div>
            
            <div class="panel-section">
                <h4>归经</h4>
                <div class="tag-list">
                    ${(props.meridians || []).map(m => `<span class="tag">${m}经</span>`).join('') || '<span style="color:#999">暂无</span>'}
                </div>
            </div>
            
            <div class="panel-section">
                <h4>相关操作</h4>
                <button class="btn btn-primary btn-sm" onclick="PanelManager.viewHerbGraph('${node.label}')">
                    查看关联图谱
                </button>
                <button class="btn btn-sm" style="margin-top:8px" onclick="PanelManager.searchHerbFormulas('${node.label}')">
                    查找含此药的方剂
                </button>
            </div>
        `;
        
        this.setContent(html);
    }
    
    showFormulaDetail(node) {
        const props = node.properties || {};
        
        fetch(`${API_BASE}/formulas/by-name/${encodeURIComponent(node.label)}`)
            .then(response => response.json())
            .then(data => {
                const herbsHtml = (data.herbs || []).map(h => 
                    `<span class="tag">${h.name} <small>${h.dosage}</small></span>`
                ).join('');
                
                const indicationsHtml = (data.indications || []).map(d => 
                    `<span class="tag">${d}</span>`
                ).join('');
                
                const html = `
                    <h3>${node.label}</h3>
                    
                    <div class="panel-section">
                        <h4>基本信息</h4>
                        <div class="info-item">
                            <span class="info-label">朝代</span>
                            <span class="info-value">${data.dynasty || '-'}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">作者</span>
                            <span class="info-value">${data.author || '-'}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">来源</span>
                            <span class="info-value">${data.source || '-'}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">剂型</span>
                            <span class="info-value">${data.form || '-'}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">使用频率</span>
                            <span class="info-value" style="color:#4caf50;font-weight:600">${data.frequency || 0} 次</span>
                        </div>
                    </div>
                    
                    <div class="panel-section">
                        <h4>主治病症</h4>
                        <div class="tag-list">
                            ${indicationsHtml || '<span style="color:#999">暂无</span>'}
                        </div>
                    </div>
                    
                    <div class="panel-section">
                        <h4>药物组成（${data.herbs ? data.herbs.length : 0}味）</h4>
                        <div class="tag-list">
                            ${herbsHtml || '<span style="color:#999">暂无</span>'}
                        </div>
                    </div>
                    
                    <div class="panel-section">
                        <h4>用法</h4>
                        <p style="font-size:13px;color:#555">${data.usage || '暂无'}</p>
                    </div>
                    
                    <div class="panel-section">
                        <button class="btn btn-primary btn-sm" onclick="PanelManager.viewFormulaGraph('${node.label}')">
                            查看方剂图谱
                        </button>
                    </div>
                `;
                
                this.setContent(html);
            })
            .catch(() => {
                const html = `
                    <h3>${node.label}</h3>
                    <div class="panel-section">
                        <div class="info-item">
                            <span class="info-label">朝代</span>
                            <span class="info-value">${props.dynasty || '-'}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">作者</span>
                            <span class="info-value">${props.author || '-'}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">使用频率</span>
                            <span class="info-value" style="color:#4caf50;font-weight:600">${props.frequency || 0} 次</span>
                        </div>
                    </div>
                    <p style="color:#999;font-size:12px">详细信息加载失败</p>
                `;
                this.setContent(html);
            });
    }
    
    showDiseaseDetail(node) {
        const props = node.properties || {};
        
        fetch(`${API_BASE}/diseases/by-name/${encodeURIComponent(node.label)}`)
            .then(response => response.json())
            .then(data => {
                const symptomsHtml = (data.symptoms || []).map(s => 
                    `<span class="tag">${s}</span>`
                ).join('');
                
                const html = `
                    <h3>${node.label}</h3>
                    
                    <div class="panel-section">
                        <h4>基本信息</h4>
                        <div class="info-item">
                            <span class="info-label">类别</span>
                            <span class="info-value">${data.category || '-'}</span>
                        </div>
                    </div>
                    
                    <div class="panel-section">
                        <h4>常见症状</h4>
                        <div class="tag-list">
                            ${symptomsHtml || '<span style="color:#999">暂无</span>'}
                        </div>
                    </div>
                    
                    <div class="panel-section">
                        <h4>相关操作</h4>
                        <button class="btn btn-primary btn-sm" onclick="PanelManager.viewDiseaseGraph('${node.label}')">
                            查看疾病图谱
                        </button>
                        <button class="btn btn-sm" style="margin-top:8px" onclick="PanelManager.searchDiseaseFormulas('${node.label}')">
                            反向查找方剂
                        </button>
                    </div>
                `;
                
                this.setContent(html);
            })
            .catch(() => {
                const html = `
                    <h3>${node.label}</h3>
                    <div class="panel-section">
                        <div class="info-item">
                            <span class="info-label">类别</span>
                            <span class="info-value">${props.category || '-'}</span>
                        </div>
                    </div>
                    <p style="color:#999;font-size:12px">详细信息加载失败</p>
                `;
                this.setContent(html);
            });
    }
    
    getNatureClass(nature) {
        if (nature.includes('温') || nature.includes('热')) return 'warm';
        if (nature.includes('寒') || nature.includes('凉')) return 'cold';
        return 'neutral';
    }
    
    static viewHerbGraph(herbName) {
        if (window.graphVis) {
            window.graphVis.loadHerbGraph(herbName);
        }
        switchView('graph');
    }
    
    static viewFormulaGraph(formulaName) {
        if (window.graphVis) {
            window.graphVis.loadFormulaGraph(formulaName);
        }
        switchView('graph');
    }
    
    static viewDiseaseGraph(diseaseName) {
        if (window.graphVis) {
            window.graphVis.loadDiseaseGraph(diseaseName);
        }
        switchView('graph');
    }
    
    static searchHerbFormulas(herbName) {
        switchView('formulas');
        const input = document.querySelector('#formula-search');
        if (input) {
            input.value = '';
        }
        loadFormulas(0, 20, null, null, herbName);
    }
    
    static searchDiseaseFormulas(diseaseName) {
        switchView('formulas');
        loadFormulas(0, 20, null, diseaseName, null);
    }
}
