/* Modern Markdown Editor - Split layout with toggleable and resizable preview */
(function() {
    'use strict';

    var editor = document.getElementById('markdown-editor');
    var preview = document.getElementById('markdown-preview');
    var contentField = document.getElementById('content');

    if (!editor || !preview) {
        console.error('MarkdownEditor: Cannot find editor or preview elements');
        return;
    }

    // Save original parent
    var originalParent = editor.parentNode;

    // Create container with split layout
    var container = document.createElement('div');
    container.style.display = 'flex';
    container.style.gap = '0';
    container.style.border = '1px solid var(--cms-border-color, #e0e0e0)';
    container.style.borderRadius = '8px';
    container.style.overflow = 'hidden';
    container.style.backgroundColor = 'var(--cms-bg, #fff)';
    container.style.position = 'relative';
    container.style.width = '100%';
    container.style.height = 'auto';
    container.style.minHeight = '450px';

    // Editor wrapper (left side)
    var editorWrap = document.createElement('div');
    editorWrap.style.flex = '1 1 60%';
    editorWrap.style.minWidth = '0';
    editorWrap.style.display = 'flex';
    editorWrap.style.flexDirection = 'column';
    editorWrap.style.height = '100%';

    // Create toolbar
    var toolbar = document.createElement('div');
    toolbar.style.display = 'flex';
    toolbar.style.gap = '4px';
    toolbar.style.padding = '8px 12px';
    toolbar.style.backgroundColor = 'var(--cms-bg-secondary, #f8f9fa)';
    toolbar.style.borderBottom = '1px solid var(--cms-border-color, #e0e0e0)';
    toolbar.style.flexWrap = 'wrap';

    var buttons = [
        { label: 'B', title: 'Bold (Ctrl+B)', prefix: '**', suffix: '**', type: 'inline' },
        { label: 'I', title: 'Italic (Ctrl+I)', prefix: '*', suffix: '*', type: 'inline' },
        { label: 'H1', title: 'Heading 1', prefix: '# ', suffix: '', type: 'block' },
        { label: 'H2', title: 'Heading 2', prefix: '## ', suffix: '', type: 'block' },
        { label: 'H3', title: 'Heading 3', prefix: '### ', suffix: '', type: 'block' },
        { label: '"', title: 'Quote', prefix: '> ', suffix: '', type: 'block' },
        { label: 'Link', title: 'Insert Link', prefix: '[', suffix: '](url)', type: 'inline' },
        { label: 'Image', title: 'Insert Image', prefix: '![', suffix: '](url)', type: 'inline' },
        { label: 'UL', title: 'Bullet List', prefix: '- ', suffix: '', type: 'block' },
        { label: 'OL', title: 'Numbered List', prefix: '1. ', suffix: '', type: 'block' },
        { label: 'HR', title: 'Horizontal Rule', prefix: '---', suffix: '', type: 'block' },
        { label: 'Code', title: 'Code Block', prefix: '```\n', suffix: '\n```', type: 'block' }
    ];

    buttons.forEach(function(btn) {
        var b = document.createElement('button');
        b.textContent = btn.label;
        b.title = btn.title;
        b.style.padding = '6px 10px';
        b.style.border = 'none';
        b.style.borderRadius = '4px';
        b.style.cursor = 'pointer';
        b.style.backgroundColor = 'transparent';
        b.style.color = 'var(--cms-text, #333)';
        b.style.fontSize = '13px';
        b.style.fontWeight = '500';
        b.style.transition = 'background-color 0.15s ease';
        b.onmouseenter = function() { this.style.backgroundColor = 'var(--cms-bg-tertiary, #e9ecef)'; };
        b.onmouseleave = function() { this.style.backgroundColor = 'transparent'; };
        b.onclick = function() { formatText(editor, btn.prefix, btn.suffix, btn.type); };
        toolbar.appendChild(b);
    });

    editorWrap.appendChild(toolbar);

    // Preview wrapper (right side)
    var previewWrap = document.createElement('div');
    previewWrap.style.flex = '1 1 40%';
    previewWrap.style.minWidth = '0';
    previewWrap.style.maxWidth = '50%';
    previewWrap.style.padding = '12px';
    previewWrap.style.overflowY = 'auto';
    previewWrap.style.backgroundColor = 'var(--cms-bg-secondary, #f8f9fa)';
    previewWrap.style.display = 'flex';
    previewWrap.style.flexDirection = 'column';
    previewWrap.style.position = 'relative';

    // Toggle button - placed on container so it's always visible
    var toggleBtn = document.createElement('button');
    toggleBtn.type = 'button';
    toggleBtn.innerHTML = 'Hide Preview';
    toggleBtn.title = 'Toggle Preview';
    toggleBtn.style.position = 'absolute';
    toggleBtn.style.top = '8px';
    toggleBtn.style.right = '8px';
    toggleBtn.style.background = 'var(--cms-bg, #fff)';
    toggleBtn.style.border = '1px solid var(--cms-border-color, #e0e0e0)';
    toggleBtn.style.borderRadius = '4px';
    toggleBtn.style.padding = '4px 8px';
    toggleBtn.style.cursor = 'pointer';
    toggleBtn.style.fontSize = '11px';
    toggleBtn.style.zIndex = '10';
    toggleBtn.onclick = function() {
        if (previewWrap.style.display === 'none') {
            previewWrap.style.display = 'flex';
            editorWrap.style.flex = '1 1 60%';
            toggleBtn.innerHTML = 'Hide Preview';
            resizeHandle.style.display = 'block';
        } else {
            previewWrap.style.display = 'none';
            editorWrap.style.flex = '1';
            toggleBtn.innerHTML = 'Show Preview';
            resizeHandle.style.display = 'none';
        }
    };
    container.appendChild(toggleBtn);
    previewWrap.appendChild(preview);

    // Resize handle
    var resizeHandle = document.createElement('div');
    resizeHandle.style.width = '8px';
    resizeHandle.style.backgroundColor = 'var(--cms-border-color, #e0e0e0)';
    resizeHandle.style.cursor = 'col-resize';
    resizeHandle.style.display = 'block';
    resizeHandle.style.transition = 'background-color 0.15s ease';
    resizeHandle.onmouseenter = function() { this.style.backgroundColor = 'var(--cms-text-muted, #888)'; };
    resizeHandle.onmouseleave = function() { this.style.backgroundColor = 'var(--cms-border-color, #e0e0e0)'; };

    // Style editor
    editor.style.flex = '1';
    editor.style.border = 'none';
    editor.style.padding = '12px';
    editor.style.fontFamily = '"Fira Code", "Consolas", "Monaco", monospace';
    editor.style.fontSize = '14px';
    editor.style.lineHeight = '1.5';
    editor.style.resize = 'none';
    editor.style.outline = 'none';
    editor.style.minHeight = '400px';
    editor.style.backgroundColor = 'transparent';
    editor.style.color = 'var(--cms-text, #333)';
    editor.style.overflowY = 'auto';

    // Style preview
    preview.style.flex = '1';
    preview.style.padding = '0';
    preview.style.minHeight = '100%';
    preview.style.color = 'var(--cms-text, #333)';
    preview.style.fontFamily = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
    preview.style.fontSize = '14px';
    preview.style.lineHeight = '1.6';
    preview.style.overflowY = 'auto';

    if (!preview.textContent.trim()) {
        preview.innerHTML = '<p style="color:var(--cms-text-muted,#888);font-style:italic;">Preview appears here...</p>';
    }

    if (contentField && contentField.value) {
        editor.value = contentField.value;
    }

    // Build container structure: editorWrap, resizeHandle, previewWrap
    container.appendChild(editorWrap);
    container.appendChild(resizeHandle);
    container.appendChild(previewWrap);
    originalParent.replaceChild(container, editor);
    editorWrap.appendChild(editor);

    // Make panes resizable
    var isResizing = false;
    var startX, startWidths;

    resizeHandle.addEventListener('mousedown', function(e) {
        isResizing = true;
        startX = e.clientX;
        startWidths = {
            editor: editorWrap.offsetWidth,
            preview: previewWrap.offsetWidth
        };
        e.preventDefault();
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
    });

    document.addEventListener('mousemove', function(e) {
        if (!isResizing) return;
        var dx = e.clientX - startX;
        var containerWidth = container.offsetWidth - resizeHandle.offsetWidth;
        var newEditorWidth = startWidths.editor + dx;
        var newPreviewWidth = startWidths.preview - dx;

        // Constrain widths to reasonable minimum
        var minWidth = 150;
        if (newEditorWidth < minWidth) {
            newEditorWidth = minWidth;
            newPreviewWidth = containerWidth - minWidth;
        }
        if (newPreviewWidth < minWidth) {
            newPreviewWidth = minWidth;
            newEditorWidth = containerWidth - minWidth;
        }

        editorWrap.style.flex = 'none';
        editorWrap.style.width = newEditorWidth + 'px';
        previewWrap.style.flex = 'none';
        previewWrap.style.width = newPreviewWidth + 'px';
    });

    document.addEventListener('mouseup', function() {
        if (isResizing) {
            isResizing = false;
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
        }
    });

    // Escape HTML special characters
    function escapeHtml(text) {
        return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    // Parse inline markdown (bold, italic, links, images)
    function parseInline(text) {
        var result = escapeHtml(text);
        result = result.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        result = result.replace(/\*(.+?)\*/g, '<em>$1</em>');
        result = result.replace(/`(.+?)`/g, '<code>$1</code>');
        result = result.replace(/\[([^\]]+)\]\(([^\)]+)\)/g, '<a href="$2">$1</a>');
        result = result.replace(/!\[([^\]]+)\]\(([^\)]+)\)/g, '<img src="$2" alt="$1" style="max-width:100%;">');
        return result;
    }

    // Markdown to HTML
    function markdownToHtml(text) {
        if (!text.trim()) {
            return '<p style="color:var(--cms-text-muted,#888);font-style:italic;">Preview appears here...</p>';
        }

        var lines = text.split('\n');
        var html = '';
        var inList = false;
        var inBlockquote = false;
        var inCodeBlock = false;
        var codeContent = '';

        for (var i = 0; i < lines.length; i++) {
            var line = lines[i];

            if (inCodeBlock) {
                if (line.match(/```/)) {
                    html += '<pre style="background:#f5f5f5;padding:12px;border-radius:4px;overflow-x:auto;"><code>' + codeContent + '</code></pre>';
                    inCodeBlock = false;
                    codeContent = '';
                } else {
                    codeContent += line + '\n';
                }
                continue;
            }

            if (line.trim() === '') {
                if (inList) {
                    html += '</ul>';
                    inList = false;
                }
                if (inBlockquote) {
                    html += '</blockquote>';
                    inBlockquote = false;
                }
                html += '<p><br></p>';
                continue;
            }

            var hMatch = line.match(/^(#+)\s+(.*)/);
            if (hMatch) {
                if (inList) {
                    html += '</ul>';
                    inList = false;
                }
                if (inBlockquote) {
                    html += '</blockquote>';
                    inBlockquote = false;
                }
                html += '<h' + hMatch[1].length + '>' + parseInline(hMatch[2]) + '</h' + hMatch[1].length + '>';
                continue;
            }

            if (line.match(/^>\s+/)) {
                if (!inBlockquote) {
                    if (inList) {
                        html += '</ul>';
                        inList = false;
                    }
                    html += '<blockquote>';
                    inBlockquote = true;
                }
                html += '<p>' + parseInline(line.substring(2).trim()) + '</p>';
                continue;
            }
            if (inBlockquote) {
                html += '</blockquote>';
                inBlockquote = false;
            }

            if (line.match(/^---+$/)) {
                if (inList) {
                    html += '</ul>';
                    inList = false;
                }
                html += '<hr style="border:0;border-top:1px solid var(--cms-border-color,#e0e0e0);margin:12px 0;">';
                continue;
            }

            var listMatch = line.match(/^\s*[-*+]\s+(.*)/);
            var olMatch = line.match(/^\s*\d+\.\s+(.*)/);
            if (listMatch || olMatch) {
                if (!inList) {
                    if (inBlockquote) {
                        html += '</blockquote>';
                        inBlockquote = false;
                    }
                    html += '<ul>';
                    inList = true;
                }
                html += '<li>' + parseInline(listMatch ? listMatch[1] : olMatch[1]) + '</li>';
                continue;
            }
            if (inList) {
                html += '</ul>';
                inList = false;
            }

            var codeMatch = line.match(/^\s*```(\w*)/);
            if (codeMatch) {
                inCodeBlock = true;
                codeContent = '';
                continue;
            }

            if (inList) {
                html += '</ul>';
                inList = false;
            }

            html += '<p>' + parseInline(line) + '</p>';
        }

        if (inCodeBlock) {
            html += '<pre style="background:#f5f5f5;padding:12px;border-radius:4px;overflow-x:auto;"><code>' + escapeHtml(codeContent) + '</code></pre>';
        }
        if (inList) html += '</ul>';
        if (inBlockquote) html += '</blockquote>';

        return html;
    }

    var previewTimeout;
    function updatePreview() {
        clearTimeout(previewTimeout);
        previewTimeout = setTimeout(function() {
            preview.innerHTML = markdownToHtml(editor.value);
        }, 300);
    }

    editor.addEventListener('input', function() {
        if (contentField) contentField.value = editor.value;
        updatePreview();
    });

    // Initial preview update
    updatePreview();

    document.addEventListener('keydown', function(e) {
        if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
            e.preventDefault();
            formatText(editor, '**', '**', 'inline');
        }
        if ((e.ctrlKey || e.metaKey) && e.key === 'i') {
            e.preventDefault();
            formatText(editor, '*', '*', 'inline');
        }
    });

    // Format helper
    function formatText(textarea, prefix, suffix, type) {
        var start = textarea.selectionStart;
        var end = textarea.selectionEnd;
        var selected = textarea.value.substring(start, end);
        var before = textarea.value.substring(0, start);
        var after = textarea.value.substring(end);

        if (type === 'block') {
            var lineStart = before.lastIndexOf('\n') + 1;
            var lineEnd = textarea.value.indexOf('\n', start);
            if (lineEnd === -1) lineEnd = textarea.value.length;
            var currentLine = textarea.value.substring(lineStart, lineEnd);

            if (currentLine.startsWith(prefix)) {
                textarea.value = before.substring(0, lineStart) + currentLine.substring(prefix.length) + after.substring(lineStart);
                textarea.selectionStart = lineStart;
                textarea.selectionEnd = lineStart + currentLine.length - prefix.length;
            } else {
                textarea.value = before.substring(0, lineStart) + prefix + currentLine + after.substring(lineStart);
                textarea.selectionStart = lineStart + prefix.length;
                textarea.selectionEnd = lineStart + prefix.length + currentLine.length;
            }
        } else {
            textarea.value = before + prefix + selected + suffix + after;
            textarea.selectionStart = start + prefix.length;
            textarea.selectionEnd = start + prefix.length + selected.length + suffix.length;
        }

        textarea.focus();
        if (contentField) contentField.value = textarea.value;
        updatePreview();
    }
})();
