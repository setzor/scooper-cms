/* Modern Markdown Editor - Split layout with toggleable preview */
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

    // Editor wrapper (left side)
    var editorWrap = document.createElement('div');
    editorWrap.style.flex = '1';
    editorWrap.style.minWidth = '0';
    editorWrap.style.display = 'flex';
    editorWrap.style.flexDirection = 'column';

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
    previewWrap.style.flex = '1';
    previewWrap.style.minWidth = '0';
    previewWrap.style.maxWidth = '400px';
    previewWrap.style.padding = '12px';
    previewWrap.style.overflowY = 'auto';
    previewWrap.style.backgroundColor = 'var(--cms-bg-secondary, #f8f9fa)';
    previewWrap.style.display = 'block';
    previewWrap.style.position = 'relative';

    // Toggle button
    var toggleBtn = document.createElement('button');
    toggleBtn.innerHTML = 'Preview';
    toggleBtn.title = 'Toggle Preview';
    toggleBtn.style.position = 'absolute';
    toggleBtn.style.top = '4px';
    toggleBtn.style.right = '4px';
    toggleBtn.style.background = 'var(--cms-bg, #fff)';
    toggleBtn.style.border = '1px solid var(--cms-border-color, #e0e0e0)';
    toggleBtn.style.borderRadius = '4px';
    toggleBtn.style.padding = '4px 8px';
    toggleBtn.style.cursor = 'pointer';
    toggleBtn.style.fontSize = '11px';
    toggleBtn.style.zIndex = '10';
    toggleBtn.onclick = function() {
        if (previewWrap.style.display === 'none') {
            previewWrap.style.display = 'block';
            toggleBtn.innerHTML = 'Preview';
        } else {
            previewWrap.style.display = 'none';
            toggleBtn.innerHTML = 'Show';
        }
    };
    previewWrap.appendChild(toggleBtn);
    previewWrap.appendChild(preview);

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

    // Style preview
    preview.style.padding = '0';
    preview.style.minHeight = '100%';
    preview.style.color = 'var(--cms-text, #333)';
    preview.style.fontFamily = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
    preview.style.fontSize = '14px';
    preview.style.lineHeight = '1.6';

    if (!preview.textContent.trim()) {
        preview.innerHTML = '<p style="color:var(--cms-text-muted,#888);font-style:italic;">Preview appears here...</p>';
    }

    if (contentField && contentField.value) {
        editor.value = contentField.value;
    }

    // CORRECT ORDER: Build container, replace editor, then move editor into place
    // 1. Build container with editorWrap and previewWrap (editor NOT in editorWrap yet)
    container.appendChild(editorWrap);
    container.appendChild(previewWrap);
    // 2. Replace editor with container in original parent
    originalParent.replaceChild(container, editor);
    // 3. NOW move editor into editorWrap (editor is now inside container via editorWrap)
    editorWrap.appendChild(editor);

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

    // Markdown to HTML
    function markdownToHtml(text) {
        if (!text.trim()) {
            return '<p style="color:var(--cms-text-muted,#888);font-style:italic;">Preview appears here...</p>';
        }

        var lines = text.split('\n');
        var html = '';

        for (var i = 0; i < lines.length; i++) {
            var line = lines[i];

            if (line.trim() === '') {
                html += '<p><br></p>';
                continue;
            }

            var hMatch = line.match(/^(#+)\s+(.*)/);
            if (hMatch) {
                html += '<h' + hMatch[1].length + '>' + hMatch[2] + '</h' + hMatch[1].length + '>';
                continue;
            }

            if (line.match(/^>\s+/)) {
                html += '<blockquote>' + line.substring(2).trim() + '</blockquote>';
                continue;
            }

            if (line.match(/^---+$/)) {
                html += '<hr style="border:0;border-top:1px solid var(--cms-border-color,#e0e0e0);margin:12px 0;">';
                continue;
            }

            var listMatch = line.match(/^\s*[-*+]\s+(.*)/);
            if (listMatch) {
                html += '<li>' + listMatch[1] + '</li>';
                continue;
            }
            var olMatch = line.match(/^\s*\d+\.\s+(.*)/);
            if (olMatch) {
                html += '<li>' + olMatch[1] + '</li>';
                continue;
            }

            if (line.match(/^\s*```/)) {
                var codeLines = [line];
                for (var j = i + 1; j < lines.length; j++) {
                    codeLines.push(lines[j]);
                    if (lines[j].match(/```/)) break;
                }
                html += '<pre style="background:#f5f5f5;padding:12px;border-radius:4px;overflow-x:auto;"><code>' + codeLines.join('\n') + '</code></pre>';
                i = j;
                continue;
            }

            html += '<p>' + line + '</p>';
        }

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
})();
