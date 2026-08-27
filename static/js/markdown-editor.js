/* Markdown Editor */
(function() {
    var editor = document.getElementById('markdown-editor');
    var preview = document.getElementById('markdown-preview');
    var content = document.getElementById('content');
    if (!editor || !preview) {
        console.error('MD Editor: elements not found');
        return;
    }
    
    // Create toolbar
    var toolbar = document.createElement('div');
    toolbar.style.cssText = 'margin-bottom:10px;display:flex;gap:5px;flex-wrap:wrap';
    
    var buttons = [
        { label: 'B', title: 'Bold', wrap: '**' },
        { label: 'I', title: 'Italic', wrap: '*' },
        { label: 'H1', title: 'Heading 1', wrap: '# ' },
        { label: 'H2', title: 'Heading 2', wrap: '## ' },
        { label: 'H3', title: 'Heading 3', wrap: '### ' },
        { label: 'Link', title: 'Insert Link', wrap: '[](url)' },
        { label: 'Image', title: 'Insert Image', wrap: '![](url)' },
        { label: 'UL', title: 'Bullet List', wrap: '- ' },
        { label: 'OL', title: 'Numbered List', wrap: '1. ' },
        { label: 'HR', title: 'Horizontal Rule', wrap: '---' }
    ];
    
    buttons.forEach(function(btn) {
        var b = document.createElement('button');
        b.textContent = btn.label;
        b.title = btn.title;
        b.style.cssText = 'padding:5px 10px;border:1px solid #ccc;border-radius:3px;cursor:pointer';
        b.onclick = function() {
            var text = editor.value;
            var start = editor.selectionStart;
            var end = editor.selectionEnd;
            var sel = text.substring(start, end);
            var before = text.substring(0, start);
            var after = text.substring(end);
            var wrap = btn.wrap;
            if (wrap) {
                var suffix = btn.label === 'HR' ? '' : wrap.split(' ')[0];
                editor.value = before + wrap + sel + suffix;
                editor.selectionStart = start + wrap.length;
                editor.selectionEnd = start + wrap.length + sel.length;
                editor.focus();
                if (content) content.value = editor.value;
            }
        };
        toolbar.appendChild(b);
    });
    
    editor.parentNode.insertBefore(toolbar, editor);
    
    // Preview styles already set in HTML, just ensure it's visible
    preview.style.display = 'block';
    if (!preview.textContent.trim()) {
        preview.textContent = 'Preview appears here as you type...';
    }
    
    // Initialize from hidden field
    if (content && content.value) {
        editor.value = content.value;
    }
    
    // Live preview with debounce
    var updatePreview = function() {
        var text = editor.value;
        if (content) content.value = text;
        if (!text.trim()) {
            preview.innerHTML = '<p style="color:var(--cms-text-muted,#888)">Preview appears here as you type...</p>';
            return;
        }
        // Basic markdown to HTML
        var html = text
            .replace(/\n\n/g, '<p></p>')
            .replace(/^#+\s+(.*)$/gm, function(m, p1) {
                var level = (m.match(/^#+/)[0] || '').length;
                return '<h' + level + '>' + p1 + '</h' + level + '>';
            })
            .replace(/^>\s+(.*)$/gm, '<blockquote>$1</blockquote>')
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.+?)\*/g, '<em>$1</em>')
            .replace(/`([^`\n]+)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
        preview.innerHTML = '<p>' + html + '</p>';
    };
    
    var timeout;
    editor.addEventListener('input', function() {
        clearTimeout(timeout);
        timeout = setTimeout(updatePreview, 300);
    });
    
    updatePreview();
})();
