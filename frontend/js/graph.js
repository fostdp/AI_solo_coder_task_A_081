const API_BASE = 'http://localhost:8000';

class GraphVisualization {
    constructor(svgSelector, canvasSelector) {
        this.svg = d3.select(svgSelector);
        this.canvas = document.querySelector(canvasSelector);
        this.ctx = this.canvas ? this.canvas.getContext('2d') : null;
        
        this.nodes = [];
        this.edges = [];
        
        this.simulation = null;
        this.zoom = null;
        this.g = null;
        this.linkGroup = null;
        this.nodeGroup = null;
        this.labelGroup = null;
        
        this.width = 0;
        this.height = 0;
        
        this.colorMap = {
            '温': '#e74c3c',
            '热': '#c0392b',
            '微温': '#e67e22',
            '平': '#95a5a6',
            '凉': '#3498db',
            '寒': '#2980b9',
            '大寒': '#1a5276',
            '微寒': '#5dade2'
        };
        
        this.init();
    }
    
    init() {
        this.resize();
        this.setupZoom();
        this.setupGroups();
        
        window.addEventListener('resize', () => {
            this.resize();
            this.updateSimulation();
        });
    }
    
    resize() {
        const container = this.svg.node().parentElement;
        this.width = container.clientWidth;
        this.height = container.clientHeight;
        
        this.svg.attr('width', this.width).attr('height', this.height);
        
        if (this.canvas) {
            this.canvas.width = this.width;
            this.canvas.height = this.height;
        }
    }
    
    setupZoom() {
        this.zoom = d3.zoom()
            .scaleExtent([0.1, 5])
            .on('zoom', (event) => {
                if (this.g) {
                    this.g.attr('transform', event.transform);
                }
            });
        
        this.svg.call(this.zoom);
    }
    
    setupGroups() {
        this.g = this.svg.append('g').attr('class', 'graph-group');
        this.linkGroup = this.g.append('g').attr('class', 'links');
        this.nodeGroup = this.g.append('g').attr('class', 'nodes');
        this.labelGroup = this.g.append('g').attr('class', 'labels');
    }
    
    getHerbColor(nature) {
        return this.colorMap[nature] || '#95a5a6';
    }
    
    getNodeSize(node) {
        if (node.type === 'formula') {
            const size = node.size || 1;
            return Math.max(8, Math.min(40, 5 + Math.sqrt(size) * 2));
        } else if (node.type === 'disease') {
            return 14;
        } else {
            return 10;
        }
    }
    
    loadData(nodeType = 'all', limit = 50) {
        let url = `${API_BASE}/graph/network?limit_per_type=${limit}`;
        
        return fetch(url)
            .then(response => response.json())
            .then(data => {
                this.nodes = data.nodes;
                this.edges = data.edges;
                this.render();
                return data;
            });
    }
    
    loadDiseaseGraph(diseaseName) {
        return fetch(`${API_BASE}/graph/disease-formulas/${encodeURIComponent(diseaseName)}`)
            .then(response => response.json())
            .then(data => {
                this.nodes = data.nodes;
                this.edges = data.edges;
                this.render();
                return data;
            });
    }
    
    loadHerbGraph(herbName) {
        return fetch(`${API_BASE}/graph/herb-formulas/${encodeURIComponent(herbName)}`)
            .then(response => response.json())
            .then(data => {
                this.nodes = data.nodes;
                this.edges = data.edges;
                this.render();
                return data;
            });
    }
    
    loadFormulaGraph(formulaName) {
        return fetch(`${API_BASE}/graph/formula-detail/${encodeURIComponent(formulaName)}`)
            .then(response => response.json())
            .then(data => {
                this.nodes = data.nodes;
                this.edges = data.edges;
                this.render();
                return data;
            });
    }
    
    render() {
        if (!this.nodes.length) return;
        
        this.linkGroup.selectAll('*').remove();
        this.nodeGroup.selectAll('*').remove();
        this.labelGroup.selectAll('*').remove();
        
        const nodeMap = new Map();
        this.nodes.forEach(n => nodeMap.set(n.id, n));
        
        const link = this.linkGroup
            .selectAll('line')
            .data(this.edges)
            .enter()
            .append('line')
            .attr('class', d => `link ${d.type || ''}`)
            .attr('stroke-width', d => d.weight ? Math.max(0.5, Math.min(3, d.weight / 100)) : 1);
        
        const node = this.nodeGroup
            .selectAll('g')
            .data(this.nodes)
            .enter()
            .append('g')
            .attr('class', d => `node ${d.type}-node`)
            .call(this.drag());
        
        node.each(function(d) {
            const sel = d3.select(this);
            const size = GraphVisualization.prototype.getNodeSize(d);
            
            if (d.type === 'herb') {
                const color = d.properties && d.properties.nature 
                    ? GraphVisualization.prototype.getHerbColor(d.properties.nature)
                    : '#95a5a6';
                sel.append('circle')
                    .attr('r', size)
                    .attr('fill', color);
            } else if (d.type === 'formula') {
                sel.append('circle')
                    .attr('r', size)
                    .attr('fill', '#f39c12');
            } else if (d.type === 'disease') {
                sel.append('circle')
                    .attr('r', size)
                    .attr('fill', '#9b59b6');
            }
        });
        
        const labels = this.labelGroup
            .selectAll('text')
            .data(this.nodes)
            .enter()
            .append('text')
            .attr('class', 'node-label')
            .text(d => d.label)
            .attr('dy', d => this.getNodeSize(d) + 12);
        
        node.on('click', (event, d) => {
            event.stopPropagation();
            this.onNodeClick(d);
        });
        
        node.on('mouseover', (event, d) => {
            this.highlightNode(d);
        });
        
        node.on('mouseout', () => {
            this.resetHighlight();
        });
        
        this.simulation = d3.forceSimulation(this.nodes)
            .force('link', d3.forceLink(this.edges).id(d => d.id).distance(d => {
                if (d.type === 'co_occurs') return 80;
                if (d.type === 'contains') return 100;
                if (d.type === 'treats') return 120;
                return 100;
            }).strength(d => {
                if (d.type === 'co_occurs') return 0.5;
                return 0.3;
            }))
            .force('charge', d3.forceManyBody().strength(d => {
                if (d.type === 'formula') return -200;
                if (d.type === 'disease') return -150;
                return -100;
            }))
            .force('center', d3.forceCenter(this.width / 2, this.height / 2))
            .force('collision', d3.forceCollide().radius(d => this.getNodeSize(d) + 5));
        
        this.simulation.on('tick', () => {
            link
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);
            
            node.attr('transform', d => `translate(${d.x}, ${d.y})`);
            labels.attr('transform', d => `translate(${d.x}, ${d.y})`);
        });
        
        this.drawCanvasBackground();
    }
    
    drawCanvasBackground() {
        if (!this.ctx) return;
        
        this.ctx.clearRect(0, 0, this.width, this.height);
        
        const gradient = this.ctx.createRadialGradient(
            this.width / 2, this.height / 2, 0,
            this.width / 2, this.height / 2, Math.max(this.width, this.height) / 2
        );
        gradient.addColorStop(0, 'rgba(250, 252, 250, 1)');
        gradient.addColorStop(1, 'rgba(240, 245, 240, 1)');
        
        this.ctx.fillStyle = gradient;
        this.ctx.fillRect(0, 0, this.width, this.height);
        
        this.ctx.strokeStyle = 'rgba(200, 220, 200, 0.3)';
        this.ctx.lineWidth = 1;
        
        const gridSize = 50;
        for (let x = 0; x < this.width; x += gridSize) {
            this.ctx.beginPath();
            this.ctx.moveTo(x, 0);
            this.ctx.lineTo(x, this.height);
            this.ctx.stroke();
        }
        for (let y = 0; y < this.height; y += gridSize) {
            this.ctx.beginPath();
            this.ctx.moveTo(0, y);
            this.ctx.lineTo(this.width, y);
            this.ctx.stroke();
        }
    }
    
    updateSimulation() {
        if (this.simulation) {
            this.simulation.force('center', d3.forceCenter(this.width / 2, this.height / 2));
            this.simulation.alpha(0.3).restart();
        }
    }
    
    drag() {
        const simulation = this.simulation;
        
        function dragstarted(event, d) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }
        
        function dragged(event, d) {
            d.fx = event.x;
            d.fy = event.y;
        }
        
        function dragended(event, d) {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }
        
        return d3.drag()
            .on('start', dragstarted)
            .on('drag', dragged)
            .on('end', dragended);
    }
    
    highlightNode(d) {
        const connectedIds = new Set([d.id]);
        
        this.edges.forEach(edge => {
            if (edge.source === d.id || edge.source.id === d.id) {
                const targetId = typeof edge.target === 'object' ? edge.target.id : edge.target;
                connectedIds.add(targetId);
            }
            if (edge.target === d.id || edge.target.id === d.id) {
                const sourceId = typeof edge.source === 'object' ? edge.source.id : edge.source;
                connectedIds.add(sourceId);
            }
        });
        
        this.nodeGroup.selectAll('.node')
            .classed('dimmed', node => !connectedIds.has(node.id));
        
        this.labelGroup.selectAll('text')
            .style('opacity', d => connectedIds.has(d.id) ? 1 : 0.3);
        
        this.linkGroup.selectAll('.link')
            .classed('dimmed', edge => {
                const sourceId = typeof edge.source === 'object' ? edge.source.id : edge.source;
                const targetId = typeof edge.target === 'object' ? edge.target.id : edge.target;
                return !(sourceId === d.id || targetId === d.id);
            })
            .classed('highlight', edge => {
                const sourceId = typeof edge.source === 'object' ? edge.source.id : edge.source;
                const targetId = typeof edge.target === 'object' ? edge.target.id : edge.target;
                return sourceId === d.id || targetId === d.id;
            });
    }
    
    resetHighlight() {
        this.nodeGroup.selectAll('.node').classed('dimmed', false);
        this.labelGroup.selectAll('text').style('opacity', 1);
        this.linkGroup.selectAll('.link').classed('dimmed', false).classed('highlight', false);
    }
    
    onNodeClick(node) {
        if (window.panelManager) {
            window.panelManager.showNodeDetail(node);
        }
    }
    
    zoomIn() {
        this.svg.transition().duration(300).call(this.zoom.scaleBy, 1.3);
    }
    
    zoomOut() {
        this.svg.transition().duration(300).call(this.zoom.scaleBy, 0.7);
    }
    
    zoomReset() {
        this.svg.transition().duration(500).call(this.zoom.transform, d3.zoomIdentity);
    }
}
