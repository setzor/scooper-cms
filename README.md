# Scooper CMS

A lightweight, modern content management platform for news sites or blogs with a focus on simplicity and using pure python.

## Features

- **Paper-style Frontend**: Beautiful newspaper-style design for your readers
- **Full CMS Backend**: Manage all your stories with an easy-to-use interface
- **Dark & Light Modes**: Toggle between themes with a single click
- **Preview Functionality**: See how stories look before publishing
- **Rich Content Support**: HTML content editing for full formatting control
- **SQLite Database**: Zero-configuration, file-based database
- **Pure Python**: Only standard library dependencies - no pip required

## Quick Start

```bash
# Navigate to the Scooper directory
cd /path/to/Scooper

# Run the server
python3 server.py
```

The application will start on `http://localhost:8000`

- **Paper Site**: `http://localhost:8000/`
- **CMS Backend**: `http://localhost:8000/cms`

## Project Structure

```
Scooper/
├── server.py           # Main application server
├── db/                 # SQLite database
│   └── scooper.db      # Database file (created on first run)
├── static/
│   ├── css/
│   │   └── style.css   # All styles (paper + CMS)
│   └── js/
│       └── script.js   # Client-side JavaScript
└── templates/
    ├── paper/
    │   ├── index.html   # Paper homepage
    │   └── story.html   # Single story view
    └── cms/
        ├── dashboard.html  # CMS dashboard
        ├── stories.html    # Stories list
        ├── create.html     # Create new story
        ├── edit.html       # Edit story
        └── settings.html   # Site settings
```

## Features Breakdown

### Paper Site (Frontend)
- Clean, newspaper-style design
- Responsive layout for all devices
- Featured stories grid
- Category tags
- Author and date information
- Link to CMS for admins

### CMS Backend
- **Dashboard**: Overview with statistics
- **Stories**: List all stories with status indicators
- **Create/Edit**: Rich text editing with HTML support
- **Preview**: See how stories look before publishing
- **Delete**: Remove stories with confirmation
- **Settings**: Configure site title, description, and theme

### Theme System
- Light and dark modes
- Persists across sessions (stored in database)
- Also saved to browser localStorage
- Smooth transitions between themes

## Configuration

Edit the configuration at the top of `server.py`:

```python
HOST = "localhost"  # Change to "0.0.0.0" for external access
PORT = 8000        # Change to any available port
```

## Adding Custom Categories

Edit the categories list in the CMS create/edit handlers in `server.py`:

```python
categories = ['General', 'Local News', 'Technology', 'Business', 'Sports', 'Entertainment', 'Announcement']
```

## Database

Scooper uses SQLite, which creates a database file automatically in the `db/` directory. No setup required!

The database includes:
- `stories` table: All news articles
- `settings` table: Site configuration

## Production Deployment (Recommended)

**⚠️ WARNING: Do NOT use `http.server` (Python's built-in server) in production!**
It is not designed for production use and may be vulnerable to DoS attacks.

### Using Caddy as Reverse Proxy

1. **Install Caddy** (follow instructions at https://caddyserver.com/docs/install)

2. **Configure Caddyfile** (already provided):
   ```bash
   # For production, replace 'localhost' with your domain in Caddyfile
   # Then start Caddy:
   caddy run
   ```

3. **Run Scooper CMS**:
   ```bash
   # Make server accessible to Caddy (bind to 0.0.0.0)
   python3 server.py
   ```

4. **Access your site**:
   - Production: `https://yourdomain.com` (HTTPS automatically enabled)
   - CMS: `https://yourdomain.com/cms` (requires authentication)

### Alternative: Using Nginx

1. **Install Nginx**:
   ```bash
   # Ubuntu/Debian
   sudo apt install nginx
   ```

2. **Configure Nginx** (create `/etc/nginx/sites-available/scooper`):
   ```nginx
   server {
       listen 80;
       server_name yourdomain.com;
       return 301 https://$host$request_uri;
   }
   
   server {
       listen 443 ssl;
       server_name yourdomain.com;
       
       ssl_certificate /path/to/cert.pem;
       ssl_certificate_key /path/to/key.pem;
       
       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

3. **Enable SSL** with Let's Encrypt (Certbot):
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d yourdomain.com
   ```

## Requirements

- Python 3.6+
- No additional dependencies (uses only standard library)

## Browser Compatibility

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Works on mobile devices

## Customization

### CSS
Edit `static/css/style.css` to customize the appearance. The file uses CSS custom properties (variables) for easy theming.

### Templates
Edit files in the `templates/` directory to change the HTML structure.

### JavaScript
Edit `static/js/script.js` to add custom client-side functionality.

## Keyboard Shortcuts

- `Ctrl/Cmd + S`: Save form (when editing a story)

## Tips

1. **First Run**: Sample stories are automatically created on first run
2. **Preview**: Click the eye icon in the stories list to preview before publishing
3. **Drafts**: Uncheck "Publish immediately" to save as draft
4. **HTML Content**: The content field supports HTML for rich formatting

## License

Scooper CMS is free to use for any purpose and is licensed with the MIT License.

## Credits

- Fonts: Google Fonts (Playfair Display, Lora, Source Serif Pro, Inter)
- Icons: Unicode emoji characters

---

<div align="center">
  <svg width="200" height="150" viewBox="0 0 200 150" xmlns="http://www.w3.org/2000/svg">
    <style>
      .tail { transform-origin: 40px 80px; animation: wag 1.5s ease-in-out infinite; }
      .ear-left { transform-origin: 65px 45px; animation: twitch 3s ease-in-out infinite; }
      .ear-right { transform-origin: 135px 45px; animation: twitch 3s ease-in-out infinite 0.2s; }
      .eye { animation: blink 4s infinite; }
      @keyframes wag {
        0%, 100% { transform: rotate(-10deg); }
        50% { transform: rotate(10deg); }
      }
      @keyframes twitch {
        0%, 100% { transform: rotate(0deg); }
        50% { transform: rotate(5deg); }
      }
      @keyframes blink {
        0%, 45%, 55%, 100% { opacity: 1; }
        50% { opacity: 0; }
      }
    </style>
    <g transform="translate(80, 30)">
      <!-- Tail -->
      <path class="tail" d="M0,60 Q20,40 40,60" stroke="#000" stroke-width="4" fill="none"/>
      <!-- Body -->
      <ellipse cx="80" cy="80" rx="60" ry="40" fill="#f5a358" stroke="#000" stroke-width="2"/>
      <!-- Head -->
      <circle cx="140" cy="60" r="35" fill="#f5a358" stroke="#000" stroke-width="2"/>
      <!-- Ears -->
      <path class="ear-left" d="M125,35 L140,25 L155,35 Z" fill="#f5a358" stroke="#000" stroke-width="2"/>
      <path class="ear-right" d="M145,35 L160,25 L175,35 Z" fill="#f5a358" stroke="#000" stroke-width="2"/>
      <!-- Eyes -->
      <circle class="eye" cx="130" cy="55" r="5" fill="#000"/>
      <circle class="eye" cx="150" cy="55" r="5" fill="#000"/>
      <!-- Nose -->
      <polygon points="140,65 135,70 145,70" fill="#ff6b6b"/>
      <!-- Whiskers -->
      <line x1="130" y1="65" x2="110" y2="65" stroke="#000" stroke-width="1"/>
      <line x1="130" y1="68" x2="110" y2="68" stroke="#000" stroke-width="1"/>
      <line x1="150" y1="65" x2="170" y2="65" stroke="#000" stroke-width="1"/>
      <line x1="150" y1="68" x2="170" y2="68" stroke="#000" stroke-width="1"/>
      <!-- Paws -->
      <circle cx="60" cy="110" r="8" fill="#f5a358" stroke="#000" stroke-width="2"/>
      <circle cx="100" cy="110" r="8" fill="#f5a358" stroke="#000" stroke-width="2"/>
    </g>
  </svg>
</div>

*Happy coding! ✨*
