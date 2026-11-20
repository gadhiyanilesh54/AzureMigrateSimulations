/* Azure Migrate Copilot — Foundry-generative chat with durable history. */
(() => {
    'use strict';

    const state = {
        conversationId: null,
        busy: false,
        provider: 'local-grounded',
    };

    const byId = (id) => document.getElementById(id);

    function setText(element, value) {
        if (element) element.textContent = value;
    }

    function scrollMessages() {
        const messages = byId('migration-chat-messages');
        if (messages) messages.scrollTop = messages.scrollHeight;
    }

    function createButton(text, className, handler) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = className;
        button.textContent = text;
        button.addEventListener('click', handler);
        return button;
    }

    function appendMessage(role, content, response = null) {
        const messages = byId('migration-chat-messages');
        if (!messages) return null;

        const row = document.createElement('div');
        row.className = `migration-chat-message ${role}`;
        row.dataset.role = role;

        const avatar = document.createElement('span');
        avatar.className = 'migration-chat-avatar';
        avatar.innerHTML = role === 'user'
            ? '<i class="bi bi-person-fill"></i>'
            : '<i class="bi bi-stars"></i>';

        const bubble = document.createElement('div');
        bubble.className = 'migration-chat-bubble';
        const body = document.createElement('div');
        body.className = 'migration-chat-answer';
        body.textContent = content;
        bubble.appendChild(body);

        if (response) {
            const meta = document.createElement('div');
            meta.className = 'migration-chat-meta';
            const provider = response.provider === 'foundry-generative'
                ? `Foundry generative · ${response.model_deployment || 'configured model'}`
                : 'Local grounded analysis';
            meta.textContent = `${provider} · ${String(response.intent || 'answer').replaceAll('_', ' ')}`;
            bubble.appendChild(meta);

            if (response.provider_warning) {
                const warning = document.createElement('div');
                warning.className = 'small text-warning mt-2';
                warning.textContent = response.provider_warning;
                bubble.appendChild(warning);
            }

            if ((response.citations || []).length) {
                const citations = document.createElement('div');
                citations.className = 'migration-chat-citations';
                for (const citation of response.citations) {
                    const chip = document.createElement('span');
                    chip.className = 'migration-chat-citation';
                    chip.title = `${citation.source || ''}${citation.route ? ` · ${citation.route}` : ''}`;
                    chip.textContent = citation.entity
                        ? `${citation.title}: ${citation.entity}`
                        : citation.title;
                    citations.appendChild(chip);
                }
                bubble.appendChild(citations);
            }

            if ((response.actions || []).length) {
                const actions = document.createElement('div');
                actions.className = 'migration-chat-actions';
                for (const action of response.actions) {
                    actions.appendChild(createButton(
                        action.label,
                        'migration-chat-action',
                        () => executeChatAction(action),
                    ));
                }
                bubble.appendChild(actions);
            }

            if ((response.suggestions || []).length) {
                const suggestions = document.createElement('div');
                suggestions.className = 'migration-chat-suggestions';
                for (const suggestion of response.suggestions.slice(0, 4)) {
                    suggestions.appendChild(createButton(
                        suggestion,
                        'migration-chat-suggestion',
                        () => sendMigrationChat(suggestion),
                    ));
                }
                bubble.appendChild(suggestions);
            }
        }

        row.append(avatar, bubble);
        messages.appendChild(row);
        scrollMessages();
        return row;
    }

    function appendWelcome() {
        appendMessage(
            'assistant',
            'Ask me about this migration project. I can explain discovered inventory, readiness, VM costs, workload targets, application groups, landing-zone architectures, performance, lifecycle risk, and the business case. Every factual response includes its evidence sources.',
            {
                intent: 'welcome',
                provider: state.provider,
                citations: [],
                actions: [],
                suggestions: [
                    'Summarize the assessment',
                    'Explain the total Azure cost',
                    'Why was App Service selected?',
                    'Generate landing zones',
                ],
            },
        );
    }

    function appendThinking() {
        const row = appendMessage('assistant', '');
        if (!row) return null;
        row.dataset.thinking = 'true';
        const body = row.querySelector('.migration-chat-answer');
        body.innerHTML = '<span class="migration-chat-thinking" aria-label="Analyzing"><span></span><span></span><span></span></span>';
        return row;
    }

    function setBusy(busy) {
        state.busy = busy;
        const send = byId('migration-chat-send');
        const input = byId('migration-chat-input');
        if (send) send.disabled = busy;
        if (input) input.disabled = busy;
    }

    function clearRenderedMessages() {
        const messages = byId('migration-chat-messages');
        if (messages) messages.innerHTML = '';
    }

    function renderStoredConversation(conversation) {
        clearRenderedMessages();
        for (const message of conversation.messages || []) {
            appendMessage(
                message.role,
                message.content,
                message.role === 'assistant' ? (message.metadata || {}) : null,
            );
        }
        if (!(conversation.messages || []).length) appendWelcome();
    }

    async function loadConversation(conversationId) {
        if (!conversationId) {
            startNewConversation();
            return;
        }
        const response = await fetch(`/api/chat/conversations/${encodeURIComponent(conversationId)}`);
        const conversation = await response.json();
        if (!response.ok) throw new Error(conversation.error || 'Unable to load conversation.');
        state.conversationId = conversation.id;
        const select = byId('migration-chat-conversation-select');
        if (select) select.value = conversation.id;
        renderStoredConversation(conversation);
    }

    async function loadConversationList(selectLatest = false) {
        const response = await fetch('/api/chat/conversations');
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || 'Unable to list conversations.');
        const conversations = payload.conversations || [];
        const select = byId('migration-chat-conversation-select');
        if (select) {
            select.innerHTML = '<option value="">New conversation</option>';
            for (const conversation of conversations) {
                const option = document.createElement('option');
                option.value = conversation.id;
                option.textContent = `${conversation.title} (${conversation.message_count})`;
                select.appendChild(option);
            }
            select.value = state.conversationId || '';
        }
        if (selectLatest && !state.conversationId && conversations.length) {
            await loadConversation(conversations[0].id);
        }
    }

    function startNewConversation() {
        state.conversationId = null;
        const select = byId('migration-chat-conversation-select');
        if (select) select.value = '';
        clearRenderedMessages();
        appendWelcome();
        byId('migration-chat-input')?.focus();
    }

    async function deleteCurrentConversation() {
        if (!state.conversationId) {
            startNewConversation();
            return;
        }
        const response = await fetch(
            `/api/chat/conversations/${encodeURIComponent(state.conversationId)}`,
            {method: 'DELETE'},
        );
        if (!response.ok && response.status !== 404) {
            const payload = await response.json();
            throw new Error(payload.error || 'Unable to delete conversation.');
        }
        state.conversationId = null;
        startNewConversation();
        await loadConversationList(false);
    }

    async function sendMigrationChat(rawMessage) {
        const message = String(rawMessage || '').trim();
        if (!message || state.busy) return;

        appendMessage('user', message);
        const input = byId('migration-chat-input');
        if (input) {
            input.value = '';
            input.style.height = '';
        }

        const thinking = appendThinking();
        setBusy(true);
        try {
            const strategy = byId('landing-zone-strategy')?.value || 'paas_preferred';
            const region = byId('landing-zone-region')?.value || 'eastus';
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    message,
                    conversation_id: state.conversationId,
                    strategy,
                    region,
                }),
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error || 'The chat request failed.');
            state.conversationId = result.conversation_id;
            appendMessage('assistant', result.answer, result);
            await loadConversationList(false);
            const select = byId('migration-chat-conversation-select');
            if (select) select.value = state.conversationId;
            thinking?.remove();
        } catch (error) {
            thinking?.remove();
            appendMessage(
                'assistant',
                `I could not complete that request: ${error.message || 'unknown error'}`,
                {intent: 'error', provider: 'local-grounded', citations: [], actions: [], suggestions: ['What can I ask?']},
            );
        } finally {
            setBusy(false);
            input?.focus();
        }
    }

    function showMainTab(tabId) {
        const tab = byId(tabId);
        if (tab && window.bootstrap) bootstrap.Tab.getOrCreateInstance(tab).show();
    }

    function showDiscoverySubTab(subTabId) {
        showMainTab('tab-decide');
        if (typeof window.showDecideSub === 'function') window.showDecideSub('decide-discovery');
        const subTab = byId(subTabId);
        if (subTab && window.bootstrap) bootstrap.Tab.getOrCreateInstance(subTab).show();
    }

    function closeChatPanel() {
        const panel = byId('migrationChatPanel');
        if (panel && window.bootstrap) bootstrap.Offcanvas.getOrCreateInstance(panel).hide();
    }

    function executeChatAction(action) {
        const target = action.target;
        if (action.type === 'chat_prompt') {
            sendMigrationChat(action.prompt || action.label);
            return;
        }
        if (action.type === 'ai_feasibility_start') {
            closeChatPanel();
            window.openAIFeasibilityAssessment?.(
                action.entity || '',
                action.category || '',
                action.intent || '',
            );
            return;
        }
        if (target === 'connect') {
            closeChatPanel();
            byId('connectOverlay')?.classList.remove('hidden');
            return;
        }
        if (target === 'overview') {
            showMainTab('tab-dashboard');
        } else if (target === 'decide-discovery') {
            showDiscoverySubTab('subtab-inventory');
        } else if (target === 'decide-inventory') {
            showDiscoverySubTab('subtab-inventory');
        } else if (target === 'decide-vm-assessment' || target === 'decide-workload-assessment') {
            showDiscoverySubTab('subtab-assessment');
        } else if (target === 'decide-vulnerability') {
            showDiscoverySubTab('subtab-vulnsla');
        } else if (target === 'decide-performance') {
            showDiscoverySubTab('subtab-inventory');
            byId('perf-status-section')?.scrollIntoView({behavior: 'smooth', block: 'center'});
        } else if (target === 'decide-businesscase') {
            showMainTab('tab-decide');
            window.showDecideSub?.('decide-businesscase');
            if (typeof window.loadBusinessCase === 'function') window.loadBusinessCase();
        } else if (target === 'decide-pricing') {
            showMainTab('tab-decide');
            window.showDecideSub?.('decide-pricing');
            if (typeof window.loadPricingComparison === 'function') window.loadPricingComparison();
        } else if (target === 'plan-apps') {
            showMainTab('tab-plan');
            window.showPlanSub?.('plan-apps');
            window.loadApplicationGroups?.();
        } else if (target === 'plan-landing-zone') {
            showMainTab('tab-plan');
            window.showPlanSub?.('plan-landing-zone');
            window.loadLandingZones?.();
        } else if (target === 'vm-whatif' && action.entity && typeof window.openWhatIf === 'function') {
            window.openWhatIf(action.entity);
        }
        closeChatPanel();
    }

    async function loadMigrationChatStatus() {
        try {
            const response = await fetch('/api/chat/status');
            const status = await response.json();
            if (!response.ok) throw new Error(status.error || 'Status unavailable');
            state.provider = status.mode || 'local-grounded';
            const foundry = status.mode === 'foundry-generative';
            byId('migration-chat-provider-dot')?.classList.toggle('foundry', foundry);
            setText(
                byId('migration-chat-provider-label'),
                foundry ? `Foundry AI · ${status.deployment}` : 'Local grounded',
            );
            setText(
                byId('migration-chat-context-label'),
                status.data_loaded
                    ? (status.history_persisted ? 'Project loaded · History persisted' : 'Migration project loaded')
                    : 'Waiting for discovery data',
            );
            const disclaimer = byId('migration-chat-disclaimer');
            if (disclaimer) disclaimer.title = status.cloud_data_notice || '';
        } catch (error) {
            setText(byId('migration-chat-context-label'), 'Chat status unavailable');
        }
    }

    async function initializeMigrationChat() {
        const form = byId('migration-chat-form');
        const input = byId('migration-chat-input');
        form?.addEventListener('submit', (event) => {
            event.preventDefault();
            sendMigrationChat(input?.value || '');
        });
        input?.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                form?.requestSubmit();
            }
        });
        input?.addEventListener('input', () => {
            input.style.height = 'auto';
            input.style.height = `${Math.min(input.scrollHeight, 130)}px`;
        });
        byId('migration-chat-clear')?.addEventListener('click', () => {
            deleteCurrentConversation().catch((error) => console.error('Delete chat failed', error));
        });
        byId('migration-chat-new')?.addEventListener('click', startNewConversation);
        byId('migration-chat-conversation-select')?.addEventListener('change', (event) => {
            loadConversation(event.target.value).catch((error) => console.error('Load chat failed', error));
        });
        document.querySelectorAll('[data-chat-prompt]').forEach((button) => {
            button.addEventListener('click', () => sendMigrationChat(button.dataset.chatPrompt || ''));
        });
        byId('migrationChatPanel')?.addEventListener('shown.bs.offcanvas', () => input?.focus());
        startNewConversation();
        await Promise.all([
            loadMigrationChatStatus(),
            loadConversationList(true),
        ]);
    }

    document.addEventListener('DOMContentLoaded', initializeMigrationChat);
    window.sendMigrationChat = sendMigrationChat;
    window.executeChatAction = executeChatAction;
})();
