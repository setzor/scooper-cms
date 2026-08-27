/* Markdown Editor - Simple inline editor with toolbar and live preview */
(function() {
    'use strict';

    var editor = document.getElementById('markdown-editor');
    var preview = document.getElementById('markdown-preview');
    var contentField = document.getElementById('content');

    if (!editor || !preview) {
        console.error('MarkdownEditor: Cannot find editor or preview elements');
        return;
    }

    // Create toolbar with formatting buttons
    var toolbar = document.createElement('div');
    toolbar.style.marginBottom = '10px';
    toolbar.style.display = 'flex';
    toolbar.style.gap = '5px';
    toolbar.style.flexWrap = 'wrap';

    var buttonConfigs = [
        { label: 'B', title: 'Bold (Ctrl+B)', prefix: '**', suffix: '**' },
        { label: 'I', title: 'Italic (Ctrl+I)', prefix: '*', suffix: '*' },
        { label: 'H1', title: 'Heading 1', prefix: '# ', suffix: '' },
        { label: 'H2', title: 'Heading 2', prefix: '## ', suffix: '' },
        { label: 'H3', title: 'Heading 3', prefix: '### ', suffix: '' },
        { label: '"', title: 'Blockquote', prefix: '> ', suffix: '' },
        { label: 'Link', title: 'Insert Link', prefix: '[', suffix: '](url)' },
        { label: 'Image', title: 'Insert Image', prefix: '![', suffix: '](url)' },
        { label: '-', title: 'Bullet List', prefix: '- ', suffix: '' },
        { label: '1.', title: 'Numbered List', prefix: '1. ', suffix: '' },
        { label: '---', title: 'Horizontal Rule', prefix: '---', suffix: '' }
    ];

    buttonConfigs.forEach(function(cfg) {
        var btn = document.createElement('button');
        btn.textContent = cfg.label;
        btn.title = cfg.title;
        btn.style.padding = '5px 10px';
        btn.style.border = '1px solid #ccc';
        btn.style.borderRadius = '3px';
        btn.style.cursor = 'pointer';
        btn.style.backgroundColor = 'var(--cms-bg-secondary, #f5f5f5)';
        btn.onclick = function() {
            wrapSelection(editor, cfg.prefix, cfg.suffix);
        };
        toolbar.appendChild(btn);
    });

    editor.parentNode.insertBefore(toolbar, editor);

    // Ensure preview is visible
    preview.style.display = 'block';
    preview.style.padding = '10px';
    preview.style.border = '1px solid var(--cms-border-color, #ddd)';
    preview.style.borderTop = 'none';
    preview.style.minHeight = '200px';
    preview.style.backgroundColor = 'var(--cms-bg-secondary, #f5f5f5)';

    if (!preview.textContent.trim()) {
        preview.textContent = 'Preview will appear here as you type...';
    }

    // Initialize from hidden content field
    if (contentField && contentField.value) {
        editor.value = contentField.value;
    }

    // Simple markdown to HTML converter
    function simpleMarkdownToHtml(text) {
        if (!text.trim()) {
            return '<p style="color:var(--cms-text-muted,#888)">Preview will appear here as you type...</p>';
        }

        var lines = text.split('\n');
        var html = '';

        lines.forEach(function(line) {
            if (line.trim() === '') {
                html += '<p><br></p>';
                return;
            }

            // Headings
            var headingMatch = line.match(/^(#+)\s+(.*)/);
            if (headingMatch) {
                var level = headingMatch[1].length;
                html += '<h' + level + '>' + headingMatch[2] + '</h' + level + '>';
                return;
            }

            // Blockquote
            if (line.match(/^>\s+/)) {
                html += '<blockquote>' + line.substring(2) + '</blockquote>';
                return;
            }

            // Horizontal rule
            if (line.match(/^---+$/)) {
                html += '<hr>';
                return;
            }

            // List items
            if (line.match(/^\s*[-*+]\s+/)) {
                html += '<li>' + line.substring(line.match(/^\s*[-*+]\s+/)[0].length) + '</li>';
                return;
            }

            if (line.match(/^\s*\d+\.\s+/)) {
                html += '<li>' + line.substring(line.match(/^\s*\d+\.\s+/)[0].length) + '</li>';
                return;
            }

            // Code block
            if (line.match(/^\s*```/)) {
                html += '<pre><code>' + line + '</code></pre>';
                return;
            }

            // Regular paragraph
            html += '<p>' + line + '</p>';
        });

        return html;
    }

    // Wrap selected text with prefix and suffix
    function wrapSelection(textarea, prefix, suffix) {
        var start = textarea.selectionStart;
        var end = textarea.selectionEnd;
        var selected = textarea.value.substring(start, end);
        var before = textarea.value.substring(0, start);
        var after = textarea.value.substring(end);

        // If no selection, use empty string
        if (selected === '') {
            selected = '';
        }

        // For block elements (H1, H2, H3, blockquote, lists, hr), add at start of line
        if (prefix === '# ' || prefix === '## ' || prefix === '### ' ||
            prefix === '> ' || prefix === '- ' || prefix === '1. ' || prefix === '---') {
            // Get current line
            var lineStart = before.lastIndexOf('\n') + 1;
            var lineEnd = textarea.value.indexOf('\n', start);
            if (lineEnd === -1) lineEnd = textarea.value.length;
            var currentLine = textarea.value.substring(lineStart, lineEnd);

            if (currentLine.trim() === '') {
                // Empty line, just add the prefix
                textarea.value = before + prefix + after;
                textarea.selectionStart = start + prefix.length;
                textarea.selectionEnd = start + prefix.length;
            } else if (currentLine.startsWith(prefix)) {
                // Already has this prefix, remove it
                textarea.value = before.substring(0, lineStart) + currentLine.substring(prefix.length) + after.substring(lineStart);
                textarea.selectionStart = start - prefix.length;
                textarea.selectionEnd = end - prefix.length;
            } else {
                // Add prefix at line start
                textarea.value = before.substring(0, lineStart) + prefix + currentLine + after.substring(lineStart);
                textarea.selectionStart = lineStart + prefix.length;
                textarea.selectionEnd = lineStart + prefix.length + currentLine.length;
            }
        } else {
            // Inline formatting
            textarea.value = before + prefix + selected + suffix + after;
            textarea.selectionStart = start + prefix.length;
            textarea.selectionEnd = start + prefix.length + selected.length + suffix.length;
        }

        textarea.focus();

        // Update content field and preview
        if (contentField) {
            contentField.value = textarea.value;
        }
        updatePreview();
    }

    // Update preview with debounce
    var previewTimeout;
    function updatePreview() {
        clearTimeout(previewTimeout);
        previewTimeout = setTimeout(function() {
            preview.innerHTML = simpleMarkdownToHtml(editor.value);
        }, 300);
    }

    // Update preview when editor changes
    editor.addEventListener('input', function() {
        if (contentField) {
            contentField.value = editor.value;
        }
        updatePreview();
    });

    // Initial preview
    updatePreview();

    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl+B for bold
        if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
            e.preventDefault();
            wrapSelection(editor, '**', '**');
        }
        // Ctrl+I for italic
        if ((e.ctrlKey || e.metaKey) && e.key === 'i') {
            e.preventDefault();
            wrapSelection(editor, '*', '*');
        }
    });
})();
