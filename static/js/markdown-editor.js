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
    
    ['B','I','H1','H2','H3','Link','Image','UL','OL','HR'].forEach(function(label) {
        var btn = document.createElement('button');
        btn.textContent = label;
        btn.title = label + ' formatting';
        btn.style.cssText = 'padding:5px 10px;border:1px solid #ccc;border-radius:3px;cursor:pointer';
        btn.onclick = function() {
            var text = editor.value;
            var start = editor.selectionStart;
            var end = editor.selectionEnd;
            var sel = text.substring(start, end);
            var before = text.substring(0, start);
            var after = text.substring(end);
            var wrapMap = {
                'B': '**',
                'I': '*',
                'H1': '# ',
                'H2': '## ',
                'H3': '### ',
                'Link': '[](url)',
                'Image': '![](url)',
                'UL': '- ',
                'OL': '1. ',
                'HR': '---'
            };
            var wrap = wrapMap[label];
            if (wrap) {
                var suffix = label === 'HR' ? '' : wrap.split(' ')[0];
                editor.value = before + wrap + sel + suffix;
                editor.selectionStart = start + wrap.length;
                editor.selectionEnd = start + wrap.length + sel.length;
                editor.focus();
                if (content) content.value = editor.value;
            }
        };
        toolbar.appendChild(btn);
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
            .replace(/

/g, '<p></p>')
            .replace(/^#+\s+(.*)$/gm, function(m, p1) {
                var level = (m.match(/^#+/)[0] || '').length;
                return '<h' + level + '>' + p1 + '</h' + level + '>';
            })
            .replace(/^>\s+(.*)$/gm, '<blockquote>$1</blockquote>')
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.+?)\*/g, '<em>$1</em>')
            .replace(/`([^`
]+)`/g, '<code>$1</code>')
            .replace(/
/g, '<br>');
        preview.innerHTML = '<p>' + html + '</p>';
    };
    
    var timeout;
    editor.addEventListener('input', function() {
        clearTimeout(timeout);
        timeout = setTimeout(updatePreview, 300);
    });
    
    updatePreview();
})();
