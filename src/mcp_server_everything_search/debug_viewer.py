"""Debug web viewer for MCP Everything Search Server.

This module contains the start_debug_web_viewer function which runs a
small HTTP server to display the rotating log file in a browser.
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import webbrowser
import time


def start_debug_web_viewer(log_file: str, logger, port: int = 8765, open_browser: bool = True, header_message: str = "🔍 MCP Everything Search Server - Debug Logs") -> None:
    """Start a simple web server to view logs in a browser.

    This is extracted from server.py to keep the server implementation
    modular and easier to test.
    
    Args:
        log_file: Path to the log file to display
        logger: Logger instance for logging viewer events
        port: Port number for the web server (default: 8765)
        open_browser: Whether to automatically open browser (default: True)
        header_message: Custom header message for the viewer (default: "🔍 MCP Everything Search Server - Debug Logs")
    """
    class LogViewerHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/':
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()

                html = fr"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>MCP Everything Search Server - Debug Logs</title>
                    <style>
                        body {{ 
                            background: #1e1e1e; 
                            color: #d4d4d4; 
                            font-family: 'Consolas', 'Monaco', 'Courier New', monospace; 
                            margin: 0;
                            padding: 0;
                            height: 100vh;
                            display: flex;
                            flex-direction: column;
                        }}
                        header {{
                            background: #252526;
                            padding: 15px 20px;
                            border-bottom: 1px solid #3e3e42;
                            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
                        }}
                        h2 {{ 
                            margin: 0;
                            color: #4ec9b0;
                            font-size: 18px;
                            font-weight: normal;
                        }}
                        .info {{
                            color: #888;
                            font-size: 12px;
                            margin-top: 5px;
                        }}
                        .controls {{
                            margin-top: 10px;
                        }}
                        button {{
                            background: #0e639c;
                            color: #fff;
                            border: none;
                            padding: 6px 12px;
                            cursor: pointer;
                            border-radius: 3px;
                            font-size: 12px;
                            margin-right: 5px;
                        }}
                        button:hover {{
                            background: #1177bb;
                        }}
                        button:active {{
                            background: #0d5a8f;
                        }}
                        #container {{
                            flex: 1;
                            overflow: hidden;
                            display: flex;
                            flex-direction: column;
                        }}
                        #logs {{ 
                            flex: 1;
                            overflow-y: auto;
                            padding: 20px;
                            white-space: pre-wrap; 
                            word-wrap: break-word;
                            font-size: 13px;
                            line-height: 1.5;
                        }}
                        .log-line {{
                            margin: 2px 0;
                        }}
                        .level-INFO {{ color: #4ec9b0; }}
                        .level-WARNING {{ color: #dcdcaa; }}
                        .level-ERROR {{ color: #f48771; }}
                        .level-DEBUG {{ color: #9cdcfe; }}
                        .level-CRITICAL {{ color: #f44747; font-weight: bold; }}
                        .timestamp {{ color: #858585; }}
                        .logger-name {{ color: #569cd6; }}
                        ::-webkit-scrollbar {{
                            width: 10px;
                        }}
                        ::-webkit-scrollbar-track {{
                            background: #1e1e1e;
                        }}
                        ::-webkit-scrollbar-thumb {{
                            background: #424242;
                            border-radius: 5px;
                        }}
                        ::-webkit-scrollbar-thumb:hover {{
                            background: #4e4e4e;
                        }}
                        .status {{
                            color: #4ec9b0;
                            font-size: 11px;
                        }}
                    </style>
                </head>
                <body>
                    <header>
                        <h2>{header_message}</h2>
                        <div class="info">
                            Log file: <code>{log_file}</code>
                            To disable this viewer, restart the server without the --debug flag.
                            Other flags are --debug-port to change port, and --no-browser to prevent auto-opening the browser.
                            <span class="status" id="status">● Live</span>
                        </div>
                        <div class="controls">
                            <button onclick="clearLogs()">Clear Display</button>
                            <button onclick="toggleAutoScroll()">Auto-scroll: <span id="scrollStatus">ON</span></button>
                            <button onclick="fetchLogs()">Refresh Now</button>
                        </div>
                    </header>
                    <div id="container">
                        <div id="logs"></div>
                    </div>
                    <script>
                        let autoScroll = true;
                        let lastContent = '';
                        
                        function escapeHtml(text) {{
                            const div = document.createElement('div');
                            div.textContent = text;
                            return div.innerHTML;
                        }}
                        
                        function formatLogLine(line) {{
                            // Try to parse log format: YYYY-MM-DD HH:MM:SS - logger - LEVEL - message
                            const match = line.match(/^(\d{{4}}-\d{{2}}-\d{{2}} \d{{2}}:\d{{2}}:\d{{2}}) - ([^ ]+) - (\w+) - (.*)$/);
                            
                            if (match) {{
                                const [, timestamp, loggerName, level, message] = match;
                                return `<div class="log-line level-${{level}}">` +
                                       `<span class="timestamp">${{escapeHtml(timestamp)}}</span> ` +
                                       `<span class="logger-name">${{escapeHtml(loggerName)}}</span> ` +
                                       `<span class="level-${{level}}">${{level}}</span> ` +
                                       `${{escapeHtml(message)}}` +
                                       `</div>`;
                            }}
                            return `<div class="log-line">${{escapeHtml(line)}}</div>`;
                        }}
                        
                        async function fetchLogs() {{
                            try {{
                                const response = await fetch('/logs');
                                const text = await response.text();
                                
                                if (text !== lastContent) {{
                                    lastContent = text;
                                    const lines = text.split('\n');
                                    const formattedLines = lines
                                        .filter(line => line.trim())
                                        .map(formatLogLine)
                                        .join('');
                                    
                                    document.getElementById('logs').innerHTML = formattedLines;
                                    
                                    if (autoScroll) {{
                                        const container = document.getElementById('logs');
                                        container.scrollTop = container.scrollHeight;
                                    }}
                                }}
                                
                                document.getElementById('status').textContent = '● Live';
                                document.getElementById('status').style.color = '#4ec9b0';
                            }} catch (error) {{
                                document.getElementById('status').textContent = '● Error';
                                document.getElementById('status').style.color = '#f48771';
                                console.error('Failed to fetch logs:', error);
                            }}
                        }}
                        
                        function clearLogs() {{
                            document.getElementById('logs').innerHTML = '<div class="log-line" style="color: #858585;">Display cleared (log file not affected)</div>';
                            lastContent = '';
                        }}
                        
                        function toggleAutoScroll() {{
                            autoScroll = !autoScroll;
                            document.getElementById('scrollStatus').textContent = autoScroll ? 'ON' : 'OFF';
                        }}
                        
                        // Fetch logs every second
                        setInterval(fetchLogs, 1000);
                        
                        // Initial fetch
                        fetchLogs();
                    </script>
                </body>
                </html>
                """
                self.wfile.write(html.encode('utf-8'))
                
            elif self.path == '/logs':
                self.send_response(200)
                self.send_header('Content-type', 'text/plain; charset=utf-8')
                self.end_headers()
                
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        # Read last 200 lines
                        lines = f.readlines()
                        recent_lines = lines[-200:]
                        self.wfile.write(''.join(recent_lines).encode('utf-8'))
                except Exception as e:
                    error_msg = f"Error reading log file: {e}\n"
                    self.wfile.write(error_msg.encode('utf-8'))
            else:
                self.send_response(404)
                self.end_headers()
        
        def log_message(self, format, *args):
            # Suppress HTTP server request logs to avoid cluttering the main log
            pass

    def run_debug_viewer_server():
        try:
            server = HTTPServer(('localhost', port), LogViewerHandler)
            logger.info(f"✓ Debug web viewer started successfully")
            logger.info(f"  URL: http://localhost:{port}")
            
            # Signal that server is ready
            server_ready.set()
            
            server.serve_forever()
        except OSError as e:
            if hasattr(e, 'errno') and e.errno in (10048, 48):  # Port already in use
                logger.error(f"Port {port} is already in use. Try a different port with --debug-port")
            else:
                logger.error(f"Failed to start debug web viewer: {e}")
        except Exception as e:
            logger.error(f"Failed to start debug web viewer: {e}", exc_info=True)

    # Event to signal when server is ready
    server_ready = threading.Event()
    
    # Start web server in a daemon thread so it doesn't block
    thread = threading.Thread(target=run_debug_viewer_server, daemon=True)
    thread.start()
    
    # Wait for server to be ready (with timeout)
    if server_ready.wait(timeout=2.0):
        # Give the server just a tiny bit more time to fully bind
        time.sleep(0.2)
        
        # Open browser automatically if requested
        if open_browser:
            url = f"http://localhost:{port}"
            try:
                logger.info(f"Opening browser to {url}")
                webbrowser.open(url, new=2)  # new=2 opens in a new tab/window
                logger.info("✓ Browser opened successfully")
            except Exception as e:
                logger.warning(f"Could not automatically open browser: {e}")
                logger.info(f"Please manually open: {url}")
    else:
        logger.warning("Server may not have started properly. Check if port is available.")
