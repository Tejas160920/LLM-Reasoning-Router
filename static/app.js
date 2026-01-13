// LLM Reasoning Router - Modern Frontend

// DOM Elements
const promptInput = document.getElementById('prompt-input');
const sendBtn = document.getElementById('send-btn');
const clearBtn = document.getElementById('clear-btn');
const chatMessages = document.getElementById('chat-messages');

// Analysis elements
const complexityScore = document.getElementById('complexity-score');
const complexityBar = document.getElementById('complexity-bar');
const complexityLevel = document.getElementById('complexity-level');
const qualityScore = document.getElementById('quality-score');
const qualityBar = document.getElementById('quality-bar');
const qualityLabel = document.getElementById('quality-label');
const modelBadge = document.getElementById('model-badge');
const modelTier = document.getElementById('model-tier');
const modelName = document.getElementById('model-name');
const signalsContainer = document.getElementById('signals-container');
const routingReasoning = document.getElementById('routing-reasoning');
const latencyDisplay = document.getElementById('latency-display');
const tokensDisplay = document.getElementById('tokens-display');
const costDisplay = document.getElementById('cost-display');

// Stats elements
const statRequests = document.getElementById('stat-requests');
const statFast = document.getElementById('stat-fast');
const statComplex = document.getElementById('stat-complex');
const statSavings = document.getElementById('stat-savings');

// Session stats
let sessionStats = {
    requests: 0,
    fast: 0,
    complex: 0,
    totalCost: 0,
    savedCost: 0
};

// Track if we've shown messages
let hasMessages = false;

// Sample prompts
document.querySelectorAll('.sample-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        promptInput.value = btn.dataset.prompt;
        promptInput.focus();
        autoResizeTextarea();
    });
});

// Event listeners
sendBtn.addEventListener('click', sendRequest);
clearBtn.addEventListener('click', clearChat);

promptInput.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        sendRequest();
    }
});

promptInput.addEventListener('input', autoResizeTextarea);

function autoResizeTextarea() {
    promptInput.style.height = 'auto';
    promptInput.style.height = Math.min(promptInput.scrollHeight, 150) + 'px';
}

// Main request function with streaming
async function sendRequest() {
    const prompt = promptInput.value.trim();
    if (!prompt) return;

    // Clear welcome message on first request
    if (!hasMessages) {
        chatMessages.innerHTML = '';
        hasMessages = true;
    }

    // Add user message
    addMessage(prompt, 'user');
    promptInput.value = '';
    autoResizeTextarea();

    // Add typing indicator
    const typingId = addTypingIndicator();

    let fullResponse = '';
    let analysisData = null;
    let usageData = null;
    const startTime = Date.now();

    try {
        const response = await fetch('/v1/chat/completions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                messages: [{ role: 'user', content: prompt }],
                include_analysis: true
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Request failed');
        }

        const data = await response.json();

        // Remove typing indicator and add assistant message
        removeTypingIndicator(typingId);
        const messageEl = addMessage(data.choices[0].message.content, 'assistant');

        // Update analysis UI if routing_info is included
        if (data.routing_info) {
            analysisData = {
                complexity_score: data.routing_info.complexity_score,
                complexity_level: data.routing_info.complexity_level,
                selected_model: data.routing_info.final_model,
                model_tier: data.routing_info.final_model.includes('flash') && !data.routing_info.final_model.includes('thinking') ? 'fast' : 'complex',
                reasoning: data.routing_info.routing_reasoning,
                detected_signals: []
            };
            updateAnalysisUI(analysisData);

            if (data.routing_info.quality_score !== undefined) {
                updateQualityUI(data.routing_info.quality_score);
            }
        }

        // Update stats
        const latency = Date.now() - startTime;
        usageData = data.usage;
        if (usageData) {
            updateMetaDisplay(latency, usageData.total_tokens, data.model);
            updateSessionStats({ selected_model: data.model }, usageData);
        }

    } catch (error) {
        removeTypingIndicator(typingId);
        addMessage(`Error: ${error.message}`, 'assistant', true);
    }
}

// Add message to chat
function addMessage(content, role, isError = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${role}`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    if (isError) contentDiv.style.color = '#ef4444';
    contentDiv.innerHTML = role === 'user' ? escapeHtml(content) : (content ? formatResponse(content) : '');

    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    return messageDiv;
}

// Add typing indicator
function addTypingIndicator() {
    const id = 'typing-' + Date.now();
    const div = document.createElement('div');
    div.id = id;
    div.className = 'message message-assistant';
    div.innerHTML = `
        <div class="typing-indicator">
            <span></span>
            <span></span>
            <span></span>
        </div>
    `;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return id;
}

// Remove typing indicator
function removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

// Update analysis UI
function updateAnalysisUI(analysis) {
    // Complexity
    complexityScore.textContent = analysis.complexity_score;
    complexityBar.style.width = analysis.complexity_score + '%';
    complexityBar.className = `progress-fill complexity ${analysis.complexity_level}`;
    complexityLevel.textContent = analysis.complexity_level;

    // Model badge
    const isFast = analysis.model_tier === 'fast';
    modelBadge.className = `model-badge ${isFast ? 'fast' : 'complex'}`;
    modelTier.textContent = isFast ? 'Flash' : 'Pro';
    modelName.textContent = analysis.selected_model;

    // Reasoning
    routingReasoning.textContent = analysis.reasoning;

    // Signals
    updateSignals(analysis.detected_signals);
}

// Update quality UI
function updateQualityUI(score) {
    qualityScore.textContent = score;
    qualityBar.style.width = score + '%';

    let level = 'good';
    let label = 'Good';
    if (score < 40) {
        level = 'poor';
        label = 'Poor';
    } else if (score < 70) {
        level = 'fair';
        label = 'Fair';
    }

    qualityBar.className = `progress-fill quality ${level}`;
    qualityLabel.textContent = label;
}

// Update signals display
function updateSignals(signals) {
    signalsContainer.innerHTML = '';

    if (!signals || signals.length === 0) {
        signalsContainer.innerHTML = '<span class="no-signals">None detected</span>';
        return;
    }

    const signalInfo = {
        'reasoning_keyword': 'Reasoning',
        'code_block': 'Code',
        'math_expression': 'Math',
        'multipart_question': 'Multi-part',
        'length': 'Long prompt'
    };

    const counts = {};
    signals.forEach(s => counts[s] = (counts[s] || 0) + 1);

    Object.entries(counts).forEach(([signal, count]) => {
        const tag = document.createElement('span');
        tag.className = `signal-tag ${signal}`;
        tag.textContent = signalInfo[signal] || signal;
        if (count > 1) tag.textContent += ` (${count})`;
        signalsContainer.appendChild(tag);
    });
}

// Update meta display
function updateMetaDisplay(latency, tokens, model) {
    latencyDisplay.textContent = `${latency}ms`;
    tokensDisplay.textContent = tokens;
    costDisplay.textContent = formatCost(estimateCost(tokens, model));
}

// Update session stats
function updateSessionStats(analysis, usage) {
    sessionStats.requests++;
    statRequests.textContent = sessionStats.requests;

    const model = analysis.selected_model;
    const isFast = model.includes('flash') && !model.includes('pro');

    if (isFast) {
        sessionStats.fast++;
        statFast.textContent = sessionStats.fast;
    } else {
        sessionStats.complex++;
        statComplex.textContent = sessionStats.complex;
    }

    // Calculate savings
    const tokens = usage.total_tokens;
    const actualCost = estimateCost(tokens, model);
    const complexCost = (tokens / 1000) * 0.00625;

    sessionStats.totalCost += actualCost;
    if (isFast) {
        sessionStats.savedCost += (complexCost - actualCost);
    }

    statSavings.textContent = formatCost(sessionStats.savedCost);
}

// Format response with markdown
function formatResponse(text) {
    let formatted = escapeHtml(text);

    // Code blocks
    formatted = formatted.replace(/```(\w*)\n([\s\S]*?)```/g,
        '<pre><code class="language-$1">$2</code></pre>');

    // Inline code
    formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Bold
    formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // Line breaks
    formatted = formatted.replace(/\n/g, '<br>');

    return formatted;
}

// Escape HTML
function escapeHtml(text) {
    return text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

// Estimate cost
function estimateCost(tokens, model) {
    const isFast = model.includes('flash') && !model.includes('pro');
    const rate = isFast ? 0.000375 : 0.00625;
    return (tokens / 1000) * rate;
}

// Format cost
function formatCost(cost) {
    if (cost >= 1) return `$${cost.toFixed(2)}`;
    if (cost >= 0.01) return `$${cost.toFixed(2)}`;
    if (cost >= 0.0001) return `$${cost.toFixed(4)}`;
    if (cost > 0) return `$${cost.toFixed(6)}`;
    return '$0.00';
}

// Clear chat
function clearChat() {
    hasMessages = false;
    chatMessages.innerHTML = `
        <div class="welcome-message">
            <div class="welcome-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                </svg>
            </div>
            <h2>LLM Reasoning Router</h2>
            <p>Intelligent model routing based on prompt complexity analysis</p>
            <div class="sample-prompts">
                <span class="samples-label">Try an example:</span>
                <div class="sample-buttons">
                    <button class="sample-btn" data-prompt="What is Python?">
                        <span class="sample-icon simple"></span>
                        Simple
                    </button>
                    <button class="sample-btn" data-prompt="Explain how a binary search tree works and when to use it">
                        <span class="sample-icon medium"></span>
                        Medium
                    </button>
                    <button class="sample-btn" data-prompt="Debug this Python code step by step and explain what is wrong:\n\n\`\`\`python\ndef factorial(n):\n    if n == 0:\n        return 1\n    return n * factorial(n)\n\`\`\`\n\nWhy does this cause infinite recursion? Provide a corrected version.">
                        <span class="sample-icon complex"></span>
                        Complex
                    </button>
                </div>
            </div>
        </div>
    `;

    // Re-attach sample button listeners
    document.querySelectorAll('.sample-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            promptInput.value = btn.dataset.prompt;
            promptInput.focus();
            autoResizeTextarea();
        });
    });

    // Reset analysis
    complexityScore.textContent = '--';
    complexityBar.style.width = '0%';
    complexityLevel.textContent = 'Waiting...';
    qualityScore.textContent = '--';
    qualityBar.style.width = '0%';
    qualityLabel.textContent = 'Waiting...';
    modelBadge.className = 'model-badge';
    modelTier.textContent = 'Waiting';
    modelName.textContent = '--';
    signalsContainer.innerHTML = '<span class="no-signals">None yet</span>';
    routingReasoning.textContent = 'Submit a prompt to see the routing analysis...';
    latencyDisplay.textContent = '--';
    tokensDisplay.textContent = '--';
    costDisplay.textContent = '--';

    promptInput.focus();
}

// Fetch metrics from backend
async function fetchMetrics() {
    try {
        const response = await fetch('/v1/metrics?period=last_day');
        if (response.ok) {
            const data = await response.json();

            const fastCount = data.requests_by_model['gemini-2.0-flash'] || 0;
            const complexCount = data.requests_by_model['gemini-2.0-flash-thinking-exp'] || 0;

            sessionStats.requests = data.total_requests;
            sessionStats.fast = fastCount;
            sessionStats.complex = complexCount;
            sessionStats.savedCost = data.cost_savings || 0;

            statRequests.textContent = sessionStats.requests;
            statFast.textContent = sessionStats.fast;
            statComplex.textContent = sessionStats.complex;
            statSavings.textContent = formatCost(sessionStats.savedCost);
        }
    } catch (error) {
        console.log('Could not fetch metrics:', error);
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    promptInput.focus();
    fetchMetrics();
});
