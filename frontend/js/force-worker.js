var ALPHA_DECAY = 0.0228;
var VELOCITY_DECAY = 0.4;
var ALPHA_MIN = 0.001;

self.onmessage = function(e) {
    var data = e.data;
    var type = data.type;

    if (type === 'init') {
        initSimulation(data);
    } else if (type === 'tick') {
        runTicks(data);
    } else if (type === 'reheat') {
        reheatSimulation(data);
    }
};

var simNodes = [];
var simEdges = [];
var alpha = 1;
var width = 0;
var height = 0;
var alphaTarget = 0;

function initSimulation(data) {
    simNodes = data.nodes;
    simEdges = data.edges;
    width = data.width || 800;
    height = data.height || 600;
    alpha = 1;
    alphaTarget = 0;

    for (var i = 0; i < simNodes.length; i++) {
        var node = simNodes[i];
        if (node.x === undefined || node.x === null) {
            node.x = width / 2 + (Math.random() - 0.5) * 200;
        }
        if (node.y === undefined || node.y === null) {
            node.y = height / 2 + (Math.random() - 0.5) * 200;
        }
        node.vx = 0;
        node.vy = 0;
    }

    for (var i = 0; i < simEdges.length; i++) {
        var edge = simEdges[i];
        if (typeof edge.source === 'object') {
            edge._sourceIdx = simNodes.indexOf(edge.source);
        } else {
            edge._sourceIdx = findNodeIdx(edge.source);
        }
        if (typeof edge.target === 'object') {
            edge._targetIdx = simNodes.indexOf(edge.target);
        } else {
            edge._targetIdx = findNodeIdx(edge.target);
        }
    }

    self.postMessage({ type: 'initialized', nodes: simNodes, edges: simEdges });
}

function findNodeIdx(id) {
    for (var i = 0; i < simNodes.length; i++) {
        if (simNodes[i].id === id) return i;
    }
    return -1;
}

function runTicks(data) {
    if (data.nodes) simNodes = data.nodes;
    if (data.alpha !== undefined) alpha = data.alpha;

    var ticks = data.ticks || 50;

    for (var t = 0; t < ticks; t++) {
        if (alpha < ALPHA_MIN) break;

        applyCenterForce();
        applyChargeForce(data.chargeStrength || -100);
        applyLinkForce(data.linkDistance || 100, data.linkStrength || 0.3);
        applyCollisionForce(data.collisionRadius || 10);

        for (var i = 0; i < simNodes.length; i++) {
            var node = simNodes[i];
            node.vx *= VELOCITY_DECAY;
            node.vy *= VELOCITY_DECAY;
            node.x += node.vx;
            node.y += node.vy;
        }

        alpha += (alphaTarget - alpha) * ALPHA_DECAY;
    }

    self.postMessage({
        type: 'tick',
        nodes: simNodes.map(function(n) {
            return { id: n.id, x: n.x, y: n.y, vx: n.vx, vy: n.vy };
        }),
        alpha: alpha,
        converged: alpha < ALPHA_MIN
    });
}

function reheatSimulation(data) {
    alpha = data.alpha || 0.5;
    self.postMessage({ type: 'reheated', alpha: alpha });
}

function applyCenterForce() {
    var cx = width / 2;
    var cy = height / 2;
    for (var i = 0; i < simNodes.length; i++) {
        var node = simNodes[i];
        node.vx += (cx - node.x) * 0.01 * alpha;
        node.vy += (cy - node.y) * 0.01 * alpha;
    }
}

function applyChargeForce(strength) {
    var n = simNodes.length;
    for (var i = 0; i < n; i++) {
        for (var j = i + 1; j < n; j++) {
            var ni = simNodes[i];
            var nj = simNodes[j];
            var dx = nj.x - ni.x;
            var dy = nj.y - ni.y;
            var dist = Math.sqrt(dx * dx + dy * dy);
            if (dist < 1) dist = 1;
            var force = strength * alpha / (dist * dist);
            ni.vx -= dx * force;
            ni.vy -= dy * force;
            nj.vx += dx * force;
            nj.vy += dy * force;
        }
    }
}

function applyLinkForce(distance, strength) {
    for (var i = 0; i < simEdges.length; i++) {
        var edge = simEdges[i];
        var si = edge._sourceIdx;
        var ti = edge._targetIdx;
        if (si < 0 || ti < 0) continue;

        var source = simNodes[si];
        var target = simNodes[ti];
        var dx = target.x - source.x;
        var dy = target.y - source.y;
        var dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 1) dist = 1;

        var linkDist = distance;
        if (edge.type === 'co_occurs') linkDist = 80;
        else if (edge.type === 'contains') linkDist = 100;
        else if (edge.type === 'treats') linkDist = 120;

        var force = (dist - linkDist) * strength * alpha / dist;
        source.vx += dx * force;
        source.vy += dy * force;
        target.vx -= dx * force;
        target.vy -= dy * force;
    }
}

function applyCollisionForce(radius) {
    for (var i = 0; i < simNodes.length; i++) {
        for (var j = i + 1; j < simNodes.length; j++) {
            var ni = simNodes[i];
            var nj = simNodes[j];
            var dx = nj.x - ni.x;
            var dy = nj.y - ni.y;
            var dist = Math.sqrt(dx * dx + dy * dy);
            var minDist = radius * 2;
            if (dist < minDist && dist > 0) {
                var overlap = (minDist - dist) / 2;
                ni.vx -= dx * overlap * alpha;
                ni.vy -= dy * overlap * alpha;
                nj.vx += dx * overlap * alpha;
                nj.vy += dy * overlap * alpha;
            }
        }
    }
}
