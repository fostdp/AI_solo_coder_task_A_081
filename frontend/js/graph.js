const API_BASE = 'http://localhost:8000';
const AGGREGATION_THRESHOLD = 150;

class GraphVisualization {
    constructor(svgSelector, canvasSelector) {
        this.svg = d3.select(svgSelector);
        this.canvas = document.querySelector(canvasSelector);
        this.ctx = this.canvas ? this.canvas.getContext('2d') : null;

        this.nodes = [];
        this.edges = [];
        this.rawNodes = [];
        this.rawEdges = [];
        this.aggregated = false;

        this.simulation = null;
        this.worker = null;
        this.useWorker = typeof Worker !== 'undefined';
        this.zoom = null;
        this.g = null;
        this.linkGroup = null;
        this.nodeGroup = null;
        this.labelGroup = null;

        this.width = 0;
        this.height = 0;

        this.colorMap = {
            '温': '#e74c3c', '热': '#c0392b', '微温': '#e67e22',
            '平': '#95a5a6', '凉': '#3498db', '寒': '#2980b9',
            '大寒': '#1a5276', '微寒': '#5dade2'
        };

        this.init();
    }

    init() {
        this.resize();
        this.setupZoom();
        this.setupGroups();
        if (this.useWorker) {
            this.initWorker();
        }

        window.addEventListener('resize', () => {
            this.resize();
            this.updateSimulation();
        });
    }

    initWorker() {
        try {
            this.worker = new Worker('js/force-worker.js');
            this.worker.onmessage = (e) => {
                var data = e.data;
                if (data.type === 'tick') {
                    this.applyWorkerPositions(data.nodes);
                    this.updatePositions();
                    if (data.converged) {
                        this.workerRunning = false;
                    } else if (this.workerRunning) {
                        this.worker.postMessage({
                            type: 'tick',
                            nodes: this.nodes,
                            ticks: 30,
                            chargeStrength: -80,
                            linkDistance: 100,
                            linkStrength: 0.2,
                            collisionRadius: 12
                        });
                    }
                }
            };
            this.workerRunning = false;
        } catch (e) {
            console.warn('WebWorker 初始化失败，回退到主线程:', e);
            this.useWorker = false;
            this.worker = null;
        }
    }

    applyWorkerPositions(positions) {
        var posMap = new Map();
        for (var i = 0; i < positions.length; i++) {
            posMap.set(positions[i].id, positions[i]);
        }
        for (var i = 0; i < this.nodes.length; i++) {
            var node = this.nodes[i];
            var pos = posMap.get(node.id);
            if (pos) {
                node.x = pos.x;
                node.y = pos.y;
                node.vx = pos.vx;
                node.vy = pos.vy;
            }
        }
    }

    updatePositions() {
        if (!this.linkGroup) return;

        this.linkGroup.selectAll('line')
            .attr('x1', d => {
                var s = typeof d.source === 'object' ? d.source : this.findNode(d.source);
                return s ? s.x : 0;
            })
            .attr('y1', d => {
                var s = typeof d.source === 'object' ? d.source : this.findNode(d.source);
                return s ? s.y : 0;
            })
            .attr('x2', d => {
                var t = typeof d.target === 'object' ? d.target : this.findNode(d.target);
                return t ? t.x : 0;
            })
            .attr('y2', d => {
                var t = typeof d.target === 'object' ? d.target : this.findNode(d.target);
                return t ? t.y : 0;
            });

        this.nodeGroup.selectAll('.node')
            .attr('transform', d => `translate(${d.x}, ${d.y})`);

        this.labelGroup.selectAll('text')
            .attr('transform', d => `translate(${d.x}, ${d.y})`);
    }

    findNode(id) {
        for (var i = 0; i < this.nodes.length; i++) {
            if (this.nodes[i].id === id) return this.nodes[i];
        }
        return null;
    }

    resize() {
        var container = this.svg.node().parentElement;
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
            var size = node.size || 1;
            return Math.max(8, Math.min(40, 5 + Math.sqrt(size) * 2));
        } else if (node.type === 'disease') {
            return 14;
        } else if (node.type === 'aggregate') {
            return Math.max(12, Math.min(30, 6 + Math.sqrt(node.count || 1) * 3));
        } else {
            return 10;
        }
    }

    aggregateNodes(nodes, edges, threshold) {
        if (nodes.length <= threshold) {
            return { nodes: nodes, edges: edges, aggregated: false };
        }

        var herbNodes = nodes.filter(n => n.type === 'herb');
        var formulaNodes = nodes.filter(n => n.type === 'formula');
        var diseaseNodes = nodes.filter(n => n.type === 'disease');

        var categoryGroups = {};
        for (var i = 0; i < herbNodes.length; i++) {
            var node = herbNodes[i];
            var cat = (node.properties && node.properties.category) || '其他';
            if (!categoryGroups[cat]) categoryGroups[cat] = [];
            categoryGroups[cat].push(node);
        }

        var aggregatedNodes = [];
        var nodeToAggId = new Map();

        for (var i = 0; i < formulaNodes.length; i++) aggregatedNodes.push(formulaNodes[i]);
        for (var i = 0; i < diseaseNodes.length; i++) aggregatedNodes.push(diseaseNodes[i]);

        var aggId = 0;
        for (var cat in categoryGroups) {
            var group = categoryGroups[cat];
            var aggNodeId = `agg_herb_${aggId}`;
            var natureCounts = {};

            for (var j = 0; j < group.length; j++) {
                nodeToAggId.set(group[j].id, aggNodeId);
                var nature = (group[j].properties && group[j].properties.nature) || '平';
                natureCounts[nature] = (natureCounts[nature] || 0) + 1;
            }

            var dominantNature = '平';
            var maxCount = 0;
            for (var n in natureCounts) {
                if (natureCounts[n] > maxCount) {
                    maxCount = natureCounts[n];
                    dominantNature = n;
                }
            }

            aggregatedNodes.push({
                id: aggNodeId,
                label: `${cat}(${group.length})`,
                type: 'aggregate',
                count: group.length,
                properties: {
                    nature: dominantNature,
                    category: cat,
                    originalIds: group.map(n => n.id)
                }
            });
            aggId++;
        }

        var aggEdges = [];
        var edgeSet = new Set();
        for (var i = 0; i < edges.length; i++) {
            var edge = edges[i];
            var srcId = typeof edge.source === 'object' ? edge.source.id : edge.source;
            var tgtId = typeof edge.target === 'object' ? edge.target.id : edge.target;

            var aggSrc = nodeToAggId.get(srcId) || srcId;
            var aggTgt = nodeToAggId.get(tgtId) || tgtId;

            var key = `${aggSrc}|${aggTgt}`;
            if (!edgeSet.has(key) && aggSrc !== aggTgt) {
                edgeSet.add(key);
                aggEdges.push({
                    source: aggSrc,
                    target: aggTgt,
                    type: edge.type || '',
                    weight: edge.weight || 1
                });
            }
        }

        return { nodes: aggregatedNodes, edges: aggEdges, aggregated: true };
    }

    loadData(nodeType, limit) {
        limit = limit || 50;
        var url = `${API_BASE}/graph/network?limit_per_type=${limit}`;

        return fetch(url)
            .then(response => response.json())
            .then(data => {
                this.rawNodes = data.nodes;
                this.rawEdges = data.edges;
                this.render();
                return data;
            });
    }

    loadDiseaseGraph(diseaseName) {
        return fetch(`${API_BASE}/graph/disease-formulas/${encodeURIComponent(diseaseName)}`)
            .then(response => response.json())
            .then(data => {
                this.rawNodes = data.nodes;
                this.rawEdges = data.edges;
                this.render();
                return data;
            });
    }

    loadHerbGraph(herbName) {
        return fetch(`${API_BASE}/graph/herb-formulas/${encodeURIComponent(herbName)}`)
            .then(response => response.json())
            .then(data => {
                this.rawNodes = data.nodes;
                this.rawEdges = data.edges;
                this.render();
                return data;
            });
    }

    loadFormulaGraph(formulaName) {
        return fetch(`${API_BASE}/graph/formula-detail/${encodeURIComponent(formulaName)}`)
            .then(response => response.json())
            .then(data => {
                this.rawNodes = data.nodes;
                this.rawEdges = data.edges;
                this.render();
                return data;
            });
    }

    render() {
        if (!this.rawNodes.length) return;

        var aggResult = this.aggregateNodes(
            this.rawNodes, this.rawEdges, AGGREGATION_THRESHOLD
        );
        this.nodes = aggResult.nodes;
        this.edges = aggResult.edges;
        this.aggregated = aggResult.aggregated;

        this.linkGroup.selectAll('*').remove();
        this.nodeGroup.selectAll('*').remove();
        this.labelGroup.selectAll('*').remove();

        var link = this.linkGroup
            .selectAll('line')
            .data(this.edges)
            .enter()
            .append('line')
            .attr('class', d => `link ${d.type || ''}`)
            .attr('stroke-width', d => d.weight ? Math.max(0.5, Math.min(3, d.weight / 100)) : 1);

        var node = this.nodeGroup
            .selectAll('g')
            .data(this.nodes)
            .enter()
            .append('g')
            .attr('class', d => `node ${d.type}-node`)
            .call(this.drag());

        var self = this;
        node.each(function(d) {
            var sel = d3.select(this);
            var size = self.getNodeSize(d);

            if (d.type === 'herb') {
                var color = d.properties && d.properties.nature
                    ? self.getHerbColor(d.properties.nature)
                    : '#95a5a6';
                sel.append('circle')
                    .attr('r', size)
                    .attr('fill', color);
            } else if (d.type === 'aggregate') {
                var color = d.properties && d.properties.nature
                    ? self.getHerbColor(d.properties.nature)
                    : '#95a5a6';
                sel.append('circle')
                    .attr('r', size)
                    .attr('fill', color)
                    .attr('stroke', '#333')
                    .attr('stroke-width', 2)
                    .attr('stroke-dasharray', '3,2');
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

        var labels = this.labelGroup
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

        if (this.useWorker && this.nodes.length > 50) {
            this.startWorkerSimulation();
        } else {
            this.startD3Simulation();
        }

        this.drawCanvasBackground();
    }

    startWorkerSimulation() {
        if (this.simulation) {
            this.simulation.stop();
        }

        var workerNodes = this.nodes.map(n => ({
            id: n.id, x: n.x, y: n.y, vx: 0, vy: 0
        }));

        var workerEdges = this.edges.map(e => ({
            source: typeof e.source === 'object' ? e.source.id : e.source,
            target: typeof e.target === 'object' ? e.target.id : e.target,
            type: e.type || '',
            weight: e.weight || 1
        }));

        this.worker.postMessage({
            type: 'init',
            nodes: workerNodes,
            edges: workerEdges,
            width: this.width,
            height: this.height
        });

        this.workerRunning = true;
        this.worker.postMessage({
            type: 'tick',
            nodes: workerNodes,
            ticks: 50,
            chargeStrength: -80,
            linkDistance: 100,
            linkStrength: 0.2,
            collisionRadius: 12
        });
    }

    startD3Simulation() {
        if (this.workerRunning) {
            this.workerRunning = false;
        }

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
                if (d.type === 'aggregate') return -300;
                return -100;
            }))
            .force('center', d3.forceCenter(this.width / 2, this.height / 2))
            .force('collision', d3.forceCollide().radius(d => this.getNodeSize(d) + 5))
            .alphaDecay(0.03);

        var link = this.linkGroup.selectAll('line');
        var node = this.nodeGroup.selectAll('.node');
        var labels = this.labelGroup.selectAll('text');

        this.simulation.on('tick', () => {
            link
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);

            node.attr('transform', d => `translate(${d.x}, ${d.y})`);
            labels.attr('transform', d => `translate(${d.x}, ${d.y})`);
        });
    }

    drawCanvasBackground() {
        if (!this.ctx) return;

        this.ctx.clearRect(0, 0, this.width, this.height);

        var gradient = this.ctx.createRadialGradient(
            this.width / 2, this.height / 2, 0,
            this.width / 2, this.height / 2, Math.max(this.width, this.height) / 2
        );
        gradient.addColorStop(0, 'rgba(250, 252, 250, 1)');
        gradient.addColorStop(1, 'rgba(240, 245, 240, 1)');

        this.ctx.fillStyle = gradient;
        this.ctx.fillRect(0, 0, this.width, this.height);

        this.ctx.strokeStyle = 'rgba(200, 220, 200, 0.3)';
        this.ctx.lineWidth = 1;

        var gridSize = 50;
        for (var x = 0; x < this.width; x += gridSize) {
            this.ctx.beginPath();
            this.ctx.moveTo(x, 0);
            this.ctx.lineTo(x, this.height);
            this.ctx.stroke();
        }
        for (var y = 0; y < this.height; y += gridSize) {
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
        var self = this;

        function dragstarted(event, d) {
            if (self.simulation) {
                if (!event.active) self.simulation.alphaTarget(0.3).restart();
            }
            d.fx = d.x;
            d.fy = d.y;
        }

        function dragged(event, d) {
            d.fx = event.x;
            d.fy = event.y;
        }

        function dragended(event, d) {
            if (self.simulation) {
                if (!event.active) self.simulation.alphaTarget(0);
            }
            d.fx = null;
            d.fy = null;
        }

        return d3.drag()
            .on('start', dragstarted)
            .on('drag', dragged)
            .on('end', dragended);
    }

    highlightNode(d) {
        var connectedIds = new Set([d.id]);

        this.edges.forEach(edge => {
            var srcId = typeof edge.source === 'object' ? edge.source.id : edge.source;
            var tgtId = typeof edge.target === 'object' ? edge.target.id : edge.target;
            if (srcId === d.id) connectedIds.add(tgtId);
            if (tgtId === d.id) connectedIds.add(srcId);
        });

        this.nodeGroup.selectAll('.node')
            .classed('dimmed', node => !connectedIds.has(node.id));

        this.labelGroup.selectAll('text')
            .style('opacity', d => connectedIds.has(d.id) ? 1 : 0.3);

        this.linkGroup.selectAll('.link')
            .classed('dimmed', edge => {
                var srcId = typeof edge.source === 'object' ? edge.source.id : edge.source;
                var tgtId = typeof edge.target === 'object' ? edge.target.id : edge.target;
                return !(srcId === d.id || tgtId === d.id);
            })
            .classed('highlight', edge => {
                var srcId = typeof edge.source === 'object' ? edge.source.id : edge.source;
                var tgtId = typeof edge.target === 'object' ? edge.target.id : edge.target;
                return srcId === d.id || tgtId === d.id;
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
