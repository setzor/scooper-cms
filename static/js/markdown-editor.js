/**
 * Scooper CMS - Markdown Editor with Live Preview
 * A lightweight markdown editor with toolbar and live preview
 */

class MarkdownEditor {
    constructor(editorId, previewId, contentId) {
        this.editor = document.getElementById(editorId);
        this.preview = document.getElementById(previewId);
        this.content = document.getElementById(contentId);
        
        if (!this.editor || !this.preview) {
            console.error('MarkdownEditor: Could not find editor or preview elements');
            return;
        }
        
        this.init();
    }
    
    init() {
        // Set initial content from hidden textarea
        if (this.content && this.content.value) {
            this.editor.value = this.content.value;
        }
        
        // Create toolbar
        this.createToolbar();
        
        // Set up live preview
        this.setupLivePreview();
        
        // Sync before form submit
        this.setupFormSync();
        
        // Load saved draft if exists
        this.loadDraft();
        
        // Set up auto-save
        this.setupAutoSave();
    }
    
    createToolbar() {
        const toolbar = document.createElement('div');
        toolbar.className = 'markdown-toolbar';
        toolbar.innerHTML = `
            <button type="button" class="toolbar-btn" title="Bold" data-action="bold">
                <b>B</b>
            </button>
            <button type="button" class="toolbar-btn" title="Italic" data-action="italic">
                <i>I</i>
            </button>
            <button type="button" class="toolbar-btn" title="Heading 1" data-action="h1">
                H1
            </button>
            <button type="button" class="toolbar-btn" title="Heading 2" data-action="h2">
                H2
            </button>
            <button type="button" class="toolbar-btn" title="Heading 3" data-action="h3">
                H3
            </button>
            <button type="button" class="toolbar-btn" title="Quote" data-action="quote">
                ""
            </button>
            <button type="button" class="toolbar-btn" title="Code" data-action="code">
                { }
            </button>
            <button type="button" class="toolbar-btn" title="Link" data-action="link">
                &#128279;
            </button>
            <button type="button" class="toolbar-btn" title="Image" data-action="image">
                &#128247;
            </button>
            <button type="button" class="toolbar-btn" title="Unordered List" data-action="ul">
                &#9679;
            </button>
            <button type="button" class="toolbar-btn" title="Ordered List" data-action="ol">
                &#9312;
            </button>
            <button type="button" class="toolbar-btn" title="Horizontal Rule" data-action="hr">
                &#8213;
            </button>
            <button type="button" class="toolbar-btn preview-toggle" title="Toggle Preview" data-action="togglePreview">
                &#128065;
            </button>
        `;
        
        // Insert toolbar before editor
        this.editor.parentNode.insertBefore(toolbar, this.editor);
        
        // Add event listeners to all buttons
        toolbar.querySelectorAll('.toolbar-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const action = e.target.closest('.toolbar-btn').dataset.action;
                this.handleAction(action);
            });
        });
        
        // Style the toolbar
        this.styleToolbar(toolbar);
    }
    
    styleToolbar(toolbar) {
        const style = document.createElement('style');
        style.textContent = `
            .markdown-toolbar {
                display: flex;
                gap: 4px;
                padding: 8px;
                background: var(--cms-sidebar-bg, #f5f5f5);
                border: 1px solid var(--cms-border-color, #ddd);
                border-radius: 6px 6px 0 0;
                margin-bottom: 0;
                flex-wrap: wrap;
            }
            
            .markdown-toolbar .toolbar-btn {
                padding: 6px 10px;
                border: 1px solid var(--cms-border-color, #ccc);
                background: var(--cms-bg, #fff);
                color: var(--cms-text, #333);
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
                transition: all 0.2s ease;
            }
            
            .markdown-toolbar .toolbar-btn:hover {
                background: var(--cms-accent-bg, #007bff);
                color: white;
                border-color: var(--cms-accent-bg, #007bff);
            }
            
            .markdown-toolbar .preview-toggle {
                margin-left: auto;
            }
            
            /* Dark theme adjustments */
            [data-theme="dark"] .markdown-toolbar {
                background: var(--cms-sidebar-bg, #2d2d2d);
            }
            
            [data-theme="dark"] .markdown-toolbar .toolbar-btn {
                background: var(--cms-bg, #1a1a1a);
                color: var(--cms-text, #e0e0e0);
                border-color: var(--cms-border-color, #444);
            }
            
            [data-theme="dark"] .markdown-toolbar .toolbar-btn:hover {
                background: var(--cms-accent-bg, #007bff);
                color: white;
            }
        `;
        document.head.appendChild(style);
    }
    
    handleAction(action) {
        const textarea = this.editor;
        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        const selectedText = textarea.value.substring(start, end);
        
        let newText = '';
        let newStart = start;
        let newEnd = end;
        
        switch (action) {
            case 'bold':
                newText = `**${selectedText}**`;
                newEnd = start + newText.length;
                break;
            case 'italic':
                newText = `*${selectedText}*`;
                newEnd = start + newText.length;
                break;
            case 'h1':
                newText = `# ${selectedText}\n`;
                newEnd = start + newText.length;
                break;
            case 'h2':
                newText = `## ${selectedText}\n`;
                newEnd = start + newText.length;
                break;
            case 'h3':
                newText = `### ${selectedText}\n`;
                newEnd = start + newText.length;
                break;
            case 'quote':
                newText = `> ${selectedText}\n`;
                newEnd = start + newText.length;
                break;
            case 'code':
                if (selectedText.includes('\n')) {
                    newText = `\n\n\`\`\`\n${selectedText}\n\`\`\`\n`;
                } else {
                    newText = `\`${selectedText}\``;
                }
                newEnd = start + newText.length;
                break;
            case 'link':
                const url = prompt('Enter URL:', 'https://');
                if (url) {
                    newText = `[${selectedText || 'link text'}](${url})`;
                    newEnd = start + newText.length;
                } else {
                    return; // User cancelled
                }
                break;
            case 'image':
                this.handleImageInsert();
                return;
            case 'ul':
                newText = `- ${selectedText}\n`;
                newEnd = start + newText.length;
                break;
            case 'ol':
                newText = `1. ${selectedText}\n`;
                newEnd = start + newText.length;
                break;
            case 'hr':
                newText = '\n---\n';
                newEnd = start + newText.length;
                break;
            case 'togglePreview':
                this.togglePreview();
                return;
        }
        
        // Replace selected text or insert at cursor
        textarea.value = textarea.value.substring(0, start) + newText + textarea.value.substring(end);
        textarea.selectionStart = newStart;
        textarea.selectionEnd = newEnd;
        textarea.focus();
        
        // Update preview
        this.renderPreview();
    }
    
    handleImageInsert() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = 'image/*';
        input.onchange = (e) => {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (event) => {
                    // For now, insert as base64. In production, you'd upload to server
                    // and insert the URL
                    const base64 = event.target.result;
                    const markdown = `![${file.name}](${base64})`;
                    
                    const textarea = this.editor;
                    const start = textarea.selectionStart;
                    const end = textarea.selectionEnd;
                    
                    textarea.value = textarea.value.substring(0, start) + markdown + textarea.value.substring(end);
                    textarea.selectionStart = start + markdown.length;
                    textarea.selectionEnd = start + markdown.length;
                    textarea.focus();
                    
                    this.renderPreview();
                };
                reader.readAsDataURL(file);
            }
        };
        input.click();
    }
    
    setupLivePreview() {
        // Debounce the preview rendering
        let timeout;
        const debouncedRender = () => {
            clearTimeout(timeout);
            timeout = setTimeout(() => this.renderPreview(), 300);
        };
        
        this.editor.addEventListener('input', debouncedRender);
        this.editor.addEventListener('change', debouncedRender);
        
        // Initial render
        this.renderPreview();
    }
    
    renderPreview() {
        const markdown = this.editor.value;
        
        // Use marked.js if available, otherwise simple formatting
        if (typeof marked !== 'undefined') {
            this.preview.innerHTML = marked.parse(markdown);
        } else {
            // Fallback: simple markdown rendering
            this.preview.innerHTML = this.simpleMarkdown(markdown);
        }
        
        // Sync hidden textarea
        if (this.content) {
            this.content.value = this.editor.value;
        }
        
        // Add preview styling
        this.ensurePreviewStyles();
    }
    
    simpleMarkdown(text) {
        // Very basic markdown rendering for fallback
        return text
            .replace(/^# (.*$)/gm, '<h1>$1</h1>')
            .replace(/^## (.*$)/gm, '<h2>$1</h2>')
            .replace(/^### (.*$)/gm, '<h3>$1</h3>')
            .replace(/^> (.*$)/gm, '<blockquote>$1</blockquote>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n\n/g, '<br><br>')
            .replace(/\n/g, '<br>')
            .replace(/---\n/g, '<hr>');
    }
    
    ensurePreviewStyles() {
        if (document.getElementById('markdown-preview-styles')) return;
        
        const style = document.createElement('style');
        style.id = 'markdown-preview-styles';
        style.textContent = `
            .markdown-preview {
                padding: 15px;
                border: 1px solid var(--cms-border-color, #ddd);
                border-radius: 0 6px 6px 6px;
                background: var(--cms-bg, #fff);
                color: var(--cms-text, #333);
                min-height: 500px;
                overflow-y: auto;
            }
            
            .markdown-preview h1 {
                font-size: 2em;
                margin: 1em 0 0.5em 0;
                border-bottom: 2px solid var(--cms-border-color, #eee);
                padding-bottom: 0.3em;
            }
            
            .markdown-preview h2 {
                font-size: 1.5em;
                margin: 1em 0 0.5em 0;
                border-bottom: 1px solid var(--cms-border-color, #eee);
                padding-bottom: 0.3em;
            }
            
            .markdown-preview h3 {
                font-size: 1.25em;
                margin: 1em 0 0.5em 0;
            }
            
            .markdown-preview p {
                margin: 0.8em 0;
                line-height: 1.6;
            }
            
            .markdown-preview blockquote {
                border-left: 4px solid var(--cms-border-color, #ccc);
                padding-left: 15px;
                margin-left: 0;
                color: var(--cms-text-secondary, #666);
                font-style: italic;
            }
            
            .markdown-preview code {
                background: var(--cms-code-bg, #f0f0f0);
                padding: 2px 4px;
                border-radius: 3px;
                font-family: monospace;
            }
            
            .markdown-preview pre {
                background: var(--cms-code-bg, #f0f0f0);
                padding: 10px;
                border-radius: 4px;
                overflow-x: auto;
            }
            
            .markdown-preview pre code {
                background: transparent;
                padding: 0;
            }
            
            .markdown-preview img {
                max-width: 100%;
                height: auto;
                border-radius: 4px;
            }
            
            .markdown-preview hr {
                border: none;
                border-top: 1px solid var(--cms-border-color, #ccc);
                margin: 1.5em 0;
            }
            
            .markdown-preview a {
                color: var(--cms-link-color, #007bff);
            }
            
            /* Dark theme */
            [data-theme="dark"] .markdown-preview {
                background: var(--cms-bg, #1a1a1a);
                color: var(--cms-text, #e0e0e0);
            }
            
            [data-theme="dark"] .markdown-preview code,
            [data-theme="dark"] .markdown-preview pre {
                background: var(--cms-code-bg, #2d2d2d);
            }
            
            [data-theme="dark"] .markdown-preview blockquote {
                color: var(--cms-text-secondary, #999);
                border-left-color: var(--cms-border-color, #444);
            }
        `;
        document.head.appendChild(style);
    }
    
    togglePreview() {
        const preview = this.preview;
        if (preview.style.display === 'none') {
            preview.style.display = 'block';
        } else {
            preview.style.display = 'none';
        }
    }
    
    setupFormSync() {
        const form = this.editor.closest('form');
        if (form) {
            form.addEventListener('submit', () => {
                // Sync the content before submit
                if (this.content) {
                    this.content.value = this.editor.value;
                }
            });
        }
    }
    
    setupAutoSave() {
        const draftKey = 'scooper-md-draft-' + (this.content ? this.content.id : 'new');
        
        // Save every 30 seconds
        setInterval(() => {
            const content = this.editor.value;
            if (content.trim()) {
                localStorage.setItem(draftKey, JSON.stringify({
                    content: content,
                    timestamp: Date.now()
                }));
            }
        }, 30000);
        
        // Load draft
        const saved = localStorage.getItem(draftKey);
        if (saved) {
            try {
                const draft = JSON.parse(saved);
                if (draft.content && !this.editor.value.trim()) {
                    if (confirm(`Found a draft from ${new Date(draft.timestamp).toLocaleString()}. Restore?`)) {
                        this.editor.value = draft.content;
                        this.renderPreview();
                    }
                }
            } catch (e) {
                console.error('Error loading draft:', e);
            }
        }
    }
    
    loadDraft() {
        // Draft loading is now handled in setupAutoSave
    }
}

// Initialize editors when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Load marked.js for markdown rendering
    const markedScript = document.createElement('script');
    markedScript.src = 'https://cdn.jsdelivr.net/npm/marked/marked.min.js';
    markedScript.onload = () => {
        // Initialize all markdown editors on the page
        const editors = document.querySelectorAll('.markdown-editor-textarea');
        editors.forEach(editor => {
            const editorId = editor.id;
            const previewId = editorId.replace('editor-', 'preview-');
            const contentId = editorId.replace('editor-', 'content-');
            new MarkdownEditor(editorId, previewId, contentId);
        });
    };
    markedScript.onerror = () => {
        console.log('marked.js failed to load, using fallback renderer');
        // Initialize with fallback
        const editors = document.querySelectorAll('.markdown-editor-textarea');
        editors.forEach(editor => {
            const editorId = editor.id;
            const previewId = editorId.replace('editor-', 'preview-');
            const contentId = editorId.replace('editor-', 'content-');
            new MarkdownEditor(editorId, previewId, contentId);
        });
    };
    document.head.appendChild(markedScript);
});
