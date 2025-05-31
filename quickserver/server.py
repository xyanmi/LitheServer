#!/usr/bin/env python3
"""
QuickServer - Core server implementation

A lightweight local file server with a beautiful web interface.

Author: @xyanmi
GitHub: https://github.com/xyanmi
"""

import os
import sys
import urllib.parse
import socket
import socketserver
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import mimetypes
import datetime
import json
import html
import tempfile
import shutil
import re
import zipfile
import base64


class QuickServerHandler(BaseHTTPRequestHandler):
    """HTTP request handler for QuickServer."""
    
    def __init__(self, *args, directory=None, **kwargs):
        self.directory = directory or os.getcwd()
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Handle GET requests."""
        self._handle_request()
    
    def do_HEAD(self):
        """Handle HEAD requests."""
        self._handle_request(head_only=True)
    
    def _handle_request(self, head_only=False):
        """Handle GET/HEAD requests."""
        try:
            # Parse URL and remove query parameters
            parsed_path = urllib.parse.urlparse(self.path)
            path = parsed_path.path
            query = urllib.parse.parse_qs(parsed_path.query)
            
            # Decode URL and normalize path
            path = urllib.parse.unquote(path)
            
            # Security check: prevent directory traversal
            if '..' in path or path.startswith('/..'):
                self.send_error(403, "Access forbidden")
                return
            
            # Handle special endpoints
            if path == '/api/preview':
                if not head_only:
                    self.handle_preview(query)
                else:
                    self.send_response(200)
                    self.end_headers()
                return
            elif path == '/api/download':
                if not head_only:
                    self.handle_download(query)
                else:
                    self.send_response(200)
                    self.end_headers()
                return
            elif path == '/api/delete':
                if not head_only:
                    self.handle_delete(query)
                else:
                    self.send_response(200)
                    self.end_headers()
                return
            elif path == '/api/move':
                if not head_only:
                    self.handle_move(query)
                else:
                    self.send_response(200)
                    self.end_headers()
                return
            elif path == '/api/rename':
                if not head_only:
                    self.handle_rename(query)
                else:
                    self.send_response(200)
                    self.end_headers()
                return
            elif path == '/api/mkdir':
                if not head_only:
                    self.handle_mkdir(query)
                else:
                    self.send_response(200)
                    self.end_headers()
                return
            elif path == '/api/zip':
                if not head_only:
                    self.handle_zip_download(query)
                else:
                    self.send_response(200)
                    self.end_headers()
                return
            elif path.startswith('/static/'):
                self.handle_static(path, head_only)
                return
            elif path == '/favicon.ico':
                self.handle_static(path, head_only)
                return
            
            # Convert URL path to filesystem path
            if path == '/':
                rel_path = ''
            else:
                rel_path = path.lstrip('/')
            
            full_path = os.path.join(self.directory, rel_path)
            full_path = os.path.normpath(full_path)
            
            # Security check: ensure path is within served directory
            if not full_path.startswith(os.path.normpath(self.directory)):
                self.send_error(403, "Access forbidden")
                return
            
            if os.path.isdir(full_path):
                if not head_only:
                    self.handle_directory(full_path, path)
                else:
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.end_headers()
            elif os.path.isfile(full_path):
                if not head_only:
                    self.handle_file(full_path)
                else:
                    self.send_response(200)
                    self.end_headers()
            else:
                self.send_error(404, "File not found")
                
        except Exception as e:
            self.send_error(500, f"Internal server error: {str(e)}")
    
    def do_POST(self):
        """Handle POST requests (file uploads)."""
        try:
            # Parse URL
            parsed_path = urllib.parse.urlparse(self.path)
            path = parsed_path.path
            
            # Only handle upload endpoint
            if path != '/api/upload':
                self.send_error(404, "Endpoint not found")
                return
            
            # Get target directory from query parameters
            query = urllib.parse.parse_qs(parsed_path.query)
            target_dir = query.get('dir', [''])[0]
            
            # Construct target directory path
            if target_dir:
                target_dir = target_dir.lstrip('/')
                target_path = os.path.join(self.directory, target_dir)
            else:
                target_path = self.directory
            
            target_path = os.path.normpath(target_path)
            
            # Security check
            if not target_path.startswith(os.path.normpath(self.directory)):
                self.send_error(403, "Access forbidden")
                return
            
            if not os.path.isdir(target_path):
                self.send_error(400, "Target directory does not exist")
                return
            
            # Parse multipart form data
            content_type = self.headers.get('Content-Type', '')
            if not content_type.startswith('multipart/form-data'):
                self.send_error(400, "Invalid content type")
                return
            
            # Get boundary
            boundary_match = re.search(r'boundary=([^;]+)', content_type)
            if not boundary_match:
                self.send_error(400, "Missing boundary in Content-Type")
                return
            
            boundary = boundary_match.group(1).strip('"')
            
            # Read content
            content_length = int(self.headers.get('Content-Length', 0))
            content = self.rfile.read(content_length)
            
            # Parse multipart data
            uploaded_files = self.parse_multipart_data(content, boundary, target_path)
            
            # Generate response
            if uploaded_files:
                response_html = self.generate_upload_success_html(uploaded_files, target_dir)
            else:
                response_html = self.generate_upload_error_html("No valid files were uploaded")
            
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(response_html.encode('utf-8'))))
            self.end_headers()
            self.wfile.write(response_html.encode('utf-8'))
            
        except Exception as e:
            self.send_error(500, f"Upload error: {str(e)}")
    
    def parse_multipart_data(self, content, boundary, target_path):
        """Parse multipart form data and save files."""
        uploaded_files = []
        boundary_bytes = f'--{boundary}'.encode()
        
        # Split content by boundary
        parts = content.split(boundary_bytes)
        
        for part in parts:
            if len(part) < 10:  # Skip empty or too small parts
                continue
            
            # Find headers and content separation
            if b'\r\n\r\n' not in part:
                continue
            
            headers_part, file_content = part.split(b'\r\n\r\n', 1)
            headers_text = headers_part.decode('utf-8', errors='ignore')
            
            # Extract filename from Content-Disposition header
            filename_match = re.search(r'filename="([^"]*)"', headers_text)
            if not filename_match:
                continue
            
            filename = filename_match.group(1)
            if not filename:
                continue
            
            # Remove trailing boundary markers
            if file_content.endswith(b'\r\n'):
                file_content = file_content[:-2]
            if file_content.endswith(b'--'):
                file_content = file_content[:-2]
            
            # Sanitize filename
            filename = self.sanitize_filename(filename)
            if not filename:
                continue
            
            file_path = os.path.join(target_path, filename)
            
            # Check if file already exists and generate unique name
            if os.path.exists(file_path):
                base, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(file_path):
                    filename = f"{base}_{counter}{ext}"
                    file_path = os.path.join(target_path, filename)
                    counter += 1
            
            # Save the file
            try:
                with open(file_path, 'wb') as f:
                    f.write(file_content)
                uploaded_files.append(filename)
            except Exception as e:
                print(f"Error saving file {filename}: {e}")
                continue
        
        return uploaded_files
    
    def sanitize_filename(self, filename):
        """Sanitize uploaded filename."""
        # Remove path components
        filename = os.path.basename(filename)
        
        # Remove or replace dangerous characters
        dangerous_chars = '<>:"/\\|?*'
        for char in dangerous_chars:
            filename = filename.replace(char, '_')
        
        # Remove leading/trailing dots and spaces
        filename = filename.strip('. ')
        
        # Ensure filename is not empty and not too long
        if not filename or len(filename) > 255:
            return None
        
        # Prevent reserved names on Windows
        reserved_names = {
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        }
        name_without_ext = os.path.splitext(filename)[0].upper()
        if name_without_ext in reserved_names:
            filename = f"file_{filename}"
        
        return filename
    
    def handle_directory(self, full_path, url_path):
        """Handle directory listing."""
        try:
            items = []
            
            # Add parent directory link if not at root
            if url_path != '/':
                parent_path = '/'.join(url_path.rstrip('/').split('/')[:-1])
                if not parent_path:
                    parent_path = '/'
                items.append({
                    'name': '..',
                    'type': 'parent',
                    'url': parent_path,
                    'size': '',
                    'modified': ''
                })
            
            # List directory contents
            for item_name in sorted(os.listdir(full_path)):
                if item_name.startswith('.'):  # Skip hidden files
                    continue
                    
                item_path = os.path.join(full_path, item_name)
                item_url = url_path.rstrip('/') + '/' + urllib.parse.quote(item_name)
                
                if os.path.isdir(item_path):
                    items.append({
                        'name': item_name,
                        'type': 'directory',
                        'url': item_url,
                        'size': '',
                        'modified': self.get_modified_time(item_path)
                    })
                else:
                    items.append({
                        'name': item_name,
                        'type': 'file',
                        'url': item_url,
                        'size': self.get_file_size(item_path),
                        'modified': self.get_modified_time(item_path),
                        'mime_type': mimetypes.guess_type(item_name)[0] or 'application/octet-stream'
                    })
            
            # Generate HTML response
            html_content = self.generate_directory_html(url_path, items)
            
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(html_content.encode('utf-8'))))
            self.end_headers()
            self.wfile.write(html_content.encode('utf-8'))
            
        except Exception as e:
            self.send_error(500, f"Error listing directory: {str(e)}")
    
    def handle_file(self, full_path):
        """Handle file requests - redirect to appropriate handler."""
        file_name = os.path.basename(full_path)
        self.handle_download({'file': [file_name]})
    
    def handle_preview(self, query):
        """Handle file preview requests."""
        if 'file' not in query:
            self.send_error(400, "Missing file parameter")
            return
        
        file_name = query['file'][0]
        
        # Get current directory from path parameter
        current_dir = query.get('path', [''])[0]
        if current_dir:
            current_dir = current_dir.lstrip('/')
            full_path = os.path.join(self.directory, current_dir, file_name)
        else:
            full_path = os.path.join(self.directory, file_name)
        
        full_path = os.path.normpath(full_path)
        
        # Security check
        if not full_path.startswith(os.path.normpath(self.directory)):
            self.send_error(403, "Access forbidden")
            return
        
        if not os.path.isfile(full_path):
            self.send_error(404, "File not found")
            return
        
        mime_type, _ = mimetypes.guess_type(full_path)
        _, ext = os.path.splitext(file_name.lower())
        
        # Define supported text file extensions for preview
        text_extensions = (
            # Programming languages
            '.py', '.pyw',           # Python
            '.js', '.jsx', '.ts', '.tsx',  # JavaScript/TypeScript
            '.json',                 # JSON
            '.html', '.htm',         # HTML
            '.css', '.scss', '.sass', '.less',  # CSS and preprocessors
            '.xml', '.xsl',          # XML
            '.yaml', '.yml',         # YAML
            '.md', '.markdown',      # Markdown
            '.txt', '.text',         # Plain text
            '.ini', '.cfg', '.conf', # Configuration files
            '.env',                  # Environment files
            
            # Shell and batch scripts
            '.sh', '.bash', '.zsh', '.fish',  # Shell scripts
            '.bat', '.cmd',          # Windows batch
            '.ps1',                  # PowerShell
            
            # System programming
            '.c', '.h',              # C
            '.cpp', '.cxx', '.cc', '.hpp', '.hxx',  # C++
            '.cs',                   # C#
            '.rs',                   # Rust
            '.go',                   # Go
            
            # Other languages
            '.java',                 # Java
            '.php', '.phtml',        # PHP
            '.rb', '.rbw',           # Ruby
            '.py',                   # Python
            '.pl', '.pm',            # Perl
            '.swift',                # Swift
            '.kt', '.kts',           # Kotlin
            '.scala',                # Scala
            '.clj', '.cljs',         # Clojure
            '.hs',                   # Haskell
            '.elm',                  # Elm
            '.lua',                  # Lua
            '.r', '.R',              # R
            '.m',                    # Objective-C / MATLAB
            '.vim',                  # Vim script
            '.dockerfile', '.containerfile',  # Docker
            
            # Data and config formats
            '.sql',                  # SQL
            '.csv', '.tsv',          # CSV/TSV
            '.log',                  # Log files
            '.properties',           # Properties files
            '.toml',                 # TOML
            '.gitignore', '.gitattributes',  # Git files
            '.editorconfig',         # Editor config
            
            # Web and markup
            '.svg',                  # SVG (text-based)
            '.rss', '.atom',         # Feed formats
            '.tex', '.latex',        # LaTeX
            '.rtf',                  # Rich Text Format
        )
        
        if mime_type and mime_type.startswith('image/'):
            self.handle_image_preview(full_path, mime_type)
        elif (mime_type and 'pdf' in mime_type.lower()) or ext == '.pdf':
            self.handle_pdf_preview(full_path, file_name)
        elif mime_type and mime_type.startswith('text/') or file_name.endswith(text_extensions):
            self.handle_text_preview(full_path, file_name)
        else:
            self.send_error(415, "Preview not supported for this file type")
    
    def handle_image_preview(self, full_path, mime_type):
        """Handle image preview."""
        try:
            with open(full_path, 'rb') as f:
                content = f.read()
            
            self.send_response(200)
            self.send_header('Content-Type', mime_type)
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Error reading image: {str(e)}")
    
    def handle_pdf_preview(self, full_path, file_name):
        """Handle PDF preview."""
        try:
            file_size = os.path.getsize(full_path)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/pdf')
            self.send_header('Content-Length', str(file_size))
            
            # Set Content-Disposition to inline for browser preview
            try:
                # Try ASCII encoding first
                file_name.encode('ascii')
                disposition = f'inline; filename="{file_name}"'
            except UnicodeEncodeError:
                # For non-ASCII filenames, use RFC 6266 encoding
                filename_encoded = urllib.parse.quote(file_name)
                disposition = f"inline; filename*=UTF-8''{filename_encoded}"
            
            self.send_header('Content-Disposition', disposition)
            self.end_headers()
            
            # Send PDF file content
            with open(full_path, 'rb') as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    
        except Exception as e:
            self.send_error(500, f"Error reading PDF: {str(e)}")
    
    def handle_text_preview(self, full_path, file_name):
        """Handle text file preview."""
        try:
            with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            html_content = self.generate_text_preview_html(file_name, content)
            
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(html_content.encode('utf-8'))))
            self.end_headers()
            self.wfile.write(html_content.encode('utf-8'))
        except Exception as e:
            self.send_error(500, f"Error reading text file: {str(e)}")
    
    def handle_download(self, query):
        """Handle file download requests."""
        if 'file' not in query:
            self.send_error(400, "Missing file parameter")
            return
        
        file_name = query['file'][0]
        
        # Get current directory from path parameter
        current_dir = query.get('path', [''])[0]
        if current_dir:
            current_dir = current_dir.lstrip('/')
            full_path = os.path.join(self.directory, current_dir, file_name)
        else:
            full_path = os.path.join(self.directory, file_name)
        
        full_path = os.path.normpath(full_path)
        
        # Security check
        if not full_path.startswith(os.path.normpath(self.directory)):
            self.send_error(403, "Access forbidden")
            return
        
        if not os.path.isfile(full_path):
            self.send_error(404, "File not found")
            return
        
        try:
            file_size = os.path.getsize(full_path)
            mime_type, _ = mimetypes.guess_type(full_path)
            
            # Get filename for download
            filename = os.path.basename(full_path)
            
            self.send_response(200)
            self.send_header('Content-Type', mime_type or 'application/octet-stream')
            self.send_header('Content-Length', str(file_size))
            
            # Handle non-ASCII filenames using RFC 6266 standard
            try:
                # Try ASCII encoding first
                filename.encode('ascii')
                disposition = f'attachment; filename="{filename}"'
            except UnicodeEncodeError:
                # For non-ASCII filenames, use RFC 6266 encoding
                filename_encoded = urllib.parse.quote(filename)
                disposition = f"attachment; filename*=UTF-8''{filename_encoded}"
            
            self.send_header('Content-Disposition', disposition)
            self.end_headers()
            
            with open(full_path, 'rb') as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
        except Exception as e:
            self.send_error(500, f"Error downloading file: {str(e)}")
    
    def handle_delete(self, query):
        """Handle file deletion requests."""
        if 'file' not in query:
            error_response = {"success": False, "message": "Missing file parameter"}
            self.send_json_response(400, error_response)
            return
        
        file_name = query['file'][0]
        
        # Get current directory from path parameter
        current_dir = query.get('path', [''])[0]
        if current_dir:
            current_dir = current_dir.lstrip('/')
            full_path = os.path.join(self.directory, current_dir, file_name)
        else:
            full_path = os.path.join(self.directory, file_name)
        
        full_path = os.path.normpath(full_path)
        
        # Security check
        if not full_path.startswith(os.path.normpath(self.directory)):
            error_response = {"success": False, "message": "Access forbidden"}
            self.send_json_response(403, error_response)
            return
        
        if not os.path.exists(full_path):
            error_response = {"success": False, "message": "File or directory not found"}
            self.send_json_response(404, error_response)
            return
        
        try:
            if os.path.isfile(full_path):
                # Delete the file
                os.remove(full_path)
                response = {"success": True, "message": "File deleted successfully"}
                self.send_json_response(200, response)
            elif os.path.isdir(full_path):
                # Check if directory is empty
                if os.listdir(full_path):
                    error_response = {"success": False, "message": "Cannot delete non-empty directory. Please remove all files and subdirectories first."}
                    self.send_json_response(400, error_response)
                    return
                # Delete the empty directory
                os.rmdir(full_path)
                response = {"success": True, "message": "Directory deleted successfully"}
                self.send_json_response(200, response)
            else:
                error_response = {"success": False, "message": "Invalid file type"}
                self.send_json_response(400, error_response)
                return
            
        except Exception as e:
            error_response = {"success": False, "message": f"Error deleting: {str(e)}"}
            self.send_json_response(500, error_response)
    
    def handle_move(self, query):
        """Handle file move requests."""
        if 'file' not in query or 'target_dir' not in query:
            error_response = {"success": False, "message": "Missing file or target directory parameter"}
            self.send_json_response(400, error_response)
            return
        
        file_name = query['file'][0]
        target_dir = query['target_dir'][0]
        
        # Get current directory from path parameter
        current_dir = query.get('path', [''])[0]
        if current_dir:
            current_dir = current_dir.lstrip('/')
            source_path = os.path.join(self.directory, current_dir, file_name)
        else:
            source_path = os.path.join(self.directory, file_name)
        
        source_path = os.path.normpath(source_path)
        
        # Construct target path - handle ".." special case
        if target_dir == '..':
            # Move to parent directory
            if current_dir:
                # If we're in a subdirectory, move to its parent
                parent_parts = current_dir.split('/')
                if len(parent_parts) > 1:
                    target_relative_dir = '/'.join(parent_parts[:-1])
                    target_full_dir = os.path.join(self.directory, target_relative_dir)
                else:
                    # Move to root directory
                    target_full_dir = self.directory
            else:
                # Already in root, can't go up
                error_response = {"success": False, "message": "Cannot move to parent directory from root"}
                self.send_json_response(400, error_response)
                return
        elif target_dir:
            # Normal directory
            target_dir = target_dir.lstrip('/')
            if current_dir:
                # Construct relative to current directory
                target_relative_dir = os.path.join(current_dir, target_dir)
            else:
                target_relative_dir = target_dir
            target_full_dir = os.path.join(self.directory, target_relative_dir)
        else:
            # Root directory
            target_full_dir = self.directory
        
        target_full_dir = os.path.normpath(target_full_dir)
        target_file_path = os.path.join(target_full_dir, file_name)
        
        # Security checks
        if not source_path.startswith(os.path.normpath(self.directory)):
            error_response = {"success": False, "message": "Source access forbidden"}
            self.send_json_response(403, error_response)
            return
        
        if not target_full_dir.startswith(os.path.normpath(self.directory)):
            error_response = {"success": False, "message": "Target access forbidden"}
            self.send_json_response(403, error_response)
            return
        
        if not os.path.isfile(source_path):
            error_response = {"success": False, "message": "Source file not found"}
            self.send_json_response(404, error_response)
            return
        
        if not os.path.isdir(target_full_dir):
            error_response = {"success": False, "message": "Target directory not found"}
            self.send_json_response(404, error_response)
            return
        
        # Check if target file already exists
        if os.path.exists(target_file_path):
            error_response = {"success": False, "message": "File already exists in target directory"}
            self.send_json_response(409, error_response)
            return
        
        try:
            # Move the file
            import shutil
            shutil.move(source_path, target_file_path)
            
            # Return success response
            response = {"success": True, "message": f"File moved successfully"}
            self.send_json_response(200, response)
            
        except Exception as e:
            error_response = {"success": False, "message": f"Error moving file: {str(e)}"}
            self.send_json_response(500, error_response)
    
    def handle_rename(self, query):
        """Handle file rename requests."""
        if 'file' not in query or 'new_name' not in query:
            error_response = {"success": False, "message": "Missing file or new name parameter"}
            self.send_json_response(400, error_response)
            return
        
        file_name = query['file'][0]
        new_name = query['new_name'][0]
        
        # Validate new name
        new_name = self.sanitize_filename(new_name)
        if not new_name:
            error_response = {"success": False, "message": "Invalid new name"}
            self.send_json_response(400, error_response)
            return
        
        # Get current directory from path parameter
        current_dir = query.get('path', [''])[0]
        if current_dir:
            current_dir = current_dir.lstrip('/')
            old_path = os.path.join(self.directory, current_dir, file_name)
            new_path = os.path.join(self.directory, current_dir, new_name)
        else:
            old_path = os.path.join(self.directory, file_name)
            new_path = os.path.join(self.directory, new_name)
        
        old_path = os.path.normpath(old_path)
        new_path = os.path.normpath(new_path)
        
        # Security checks
        if not old_path.startswith(os.path.normpath(self.directory)):
            error_response = {"success": False, "message": "Access forbidden"}
            self.send_json_response(403, error_response)
            return
        
        if not new_path.startswith(os.path.normpath(self.directory)):
            error_response = {"success": False, "message": "Invalid new name"}
            self.send_json_response(403, error_response)
            return
        
        if not os.path.exists(old_path):
            error_response = {"success": False, "message": "File or directory not found"}
            self.send_json_response(404, error_response)
            return
        
        if os.path.exists(new_path):
            error_response = {"success": False, "message": "A file or directory with that name already exists"}
            self.send_json_response(409, error_response)
            return
        
        try:
            # Rename the file or directory
            os.rename(old_path, new_path)
            
            # Return success response
            response = {"success": True, "message": f"Renamed successfully"}
            self.send_json_response(200, response)
            
        except Exception as e:
            error_response = {"success": False, "message": f"Error renaming: {str(e)}"}
            self.send_json_response(500, error_response)
    
    def handle_mkdir(self, query):
        """Handle directory creation requests."""
        if 'dir' not in query:
            error_response = {"success": False, "message": "Missing directory parameter"}
            self.send_json_response(400, error_response)
            return
        
        dir_name = query['dir'][0]
        
        # Validate directory name
        dir_name = self.sanitize_filename(dir_name)
        if not dir_name:
            error_response = {"success": False, "message": "Invalid directory name"}
            self.send_json_response(400, error_response)
            return
        
        # Get current directory from path parameter
        current_dir = query.get('path', [''])[0]
        if current_dir:
            current_dir = current_dir.lstrip('/')
            full_path = os.path.join(self.directory, current_dir, dir_name)
        else:
            full_path = os.path.join(self.directory, dir_name)
        
        full_path = os.path.normpath(full_path)
        
        # Security check
        if not full_path.startswith(os.path.normpath(self.directory)):
            error_response = {"success": False, "message": "Access forbidden"}
            self.send_json_response(403, error_response)
            return
        
        if os.path.exists(full_path):
            error_response = {"success": False, "message": "Directory already exists"}
            self.send_json_response(409, error_response)
            return
        
        try:
            # Create the directory
            os.makedirs(full_path)
            
            # Return success response
            response = {"success": True, "message": f"Directory created successfully"}
            self.send_json_response(200, response)
            
        except Exception as e:
            error_response = {"success": False, "message": f"Error creating directory: {str(e)}"}
            self.send_json_response(500, error_response)
    
    def handle_zip_download(self, query):
        """Handle zip download requests."""
        if 'dir' not in query:
            error_response = {"success": False, "message": "Missing directory parameter"}
            self.send_json_response(400, error_response)
            return
        
        dir_name = query['dir'][0]
        
        # Validate directory name
        dir_name = self.sanitize_filename(dir_name)
        if not dir_name:
            error_response = {"success": False, "message": "Invalid directory name"}
            self.send_json_response(400, error_response)
            return
        
        # Get current directory from path parameter
        current_dir = query.get('path', [''])[0]
        if current_dir:
            current_dir = current_dir.lstrip('/')
            full_path = os.path.join(self.directory, current_dir, dir_name)
        else:
            full_path = os.path.join(self.directory, dir_name)
        
        full_path = os.path.normpath(full_path)
        
        # Security check
        if not full_path.startswith(os.path.normpath(self.directory)):
            error_response = {"success": False, "message": "Access forbidden"}
            self.send_json_response(403, error_response)
            return
        
        if not os.path.isdir(full_path):
            error_response = {"success": False, "message": "Directory not found"}
            self.send_json_response(404, error_response)
            return
        
        try:
            # Create a temporary directory to store the zip file
            with tempfile.TemporaryDirectory() as temp_dir:
                # Create the zip file
                zip_path = os.path.join(temp_dir, f"{dir_name}.zip")
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    # Add all files and directories to the zip file
                    for root, _, files in os.walk(full_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, full_path)
                            zipf.write(file_path, arcname)
                
                # Send the zip file as a response
                zip_size = os.path.getsize(zip_path)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/zip')
                self.send_header('Content-Length', str(zip_size))
                
                # Handle non-ASCII filenames for download
                zip_filename = f"{dir_name}.zip"
                try:
                    # Try ASCII encoding first
                    zip_filename.encode('ascii')
                    disposition = f'attachment; filename="{zip_filename}"'
                except UnicodeEncodeError:
                    # For non-ASCII filenames, use RFC 6266 encoding
                    filename_encoded = urllib.parse.quote(zip_filename)
                    disposition = f"attachment; filename*=UTF-8''{filename_encoded}"
                
                self.send_header('Content-Disposition', disposition)
                self.end_headers()
                
                # Stream the zip file content
                with open(zip_path, 'rb') as f:
                    while True:
                        chunk = f.read(8192)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
            
        except Exception as e:
            error_response = {"success": False, "message": f"Error zipping directory: {str(e)}"}
            self.send_json_response(500, error_response)
    
    def send_json_response(self, status_code, data):
        """Send JSON response with proper headers."""
        response_json = json.dumps(data)
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(response_json.encode('utf-8'))))
        self.end_headers()
        self.wfile.write(response_json.encode('utf-8'))
    
    def handle_static(self, path, head_only=False):
        """Handle static resource requests."""
        if path == '/static/style.css':
            css_content = self.get_css_content()
            self.send_response(200)
            self.send_header('Content-Type', 'text/css')
            self.send_header('Content-Length', str(len(css_content.encode('utf-8'))))
            self.end_headers()
            if not head_only:
                self.wfile.write(css_content.encode('utf-8'))
        elif path == '/favicon.ico':
            # Serve the favicon
            favicon_content = self.get_favicon_content()
            self.send_response(200)
            self.send_header('Content-Type', 'image/svg+xml')
            self.send_header('Content-Length', str(len(favicon_content.encode('utf-8'))))
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            self.end_headers()
            if not head_only:
                self.wfile.write(favicon_content.encode('utf-8'))
        else:
            self.send_error(404, "Static resource not found")
    
    def get_favicon_content(self):
        """Return SVG favicon content."""
        # A bright, obvious SVG favicon that should be very noticeable
        return '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
            <defs>
                <linearGradient id="rocketGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" style="stop-color:#ff0066;stop-opacity:1" />
                    <stop offset="50%" style="stop-color:#3366ff;stop-opacity:1" />
                    <stop offset="100%" style="stop-color:#00cc99;stop-opacity:1" />
                </linearGradient>
                <linearGradient id="flameGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" style="stop-color:#ff3300;stop-opacity:1" />
                    <stop offset="50%" style="stop-color:#ffaa00;stop-opacity:1" />
                    <stop offset="100%" style="stop-color:#ffff00;stop-opacity:1" />
                </linearGradient>
            </defs>
            
            <!-- Background circle for contrast -->
            <circle cx="16" cy="16" r="15" fill="white" stroke="#333" stroke-width="1"/>
            
            <!-- Rocket body -->
            <ellipse cx="16" cy="14" rx="4" ry="8" fill="url(#rocketGrad)" stroke="#333" stroke-width="1"/>
            
            <!-- Rocket nose -->
            <polygon points="16,6 12,12 20,12" fill="url(#rocketGrad)" stroke="#333" stroke-width="1"/>
            
            <!-- Rocket fins -->
            <polygon points="12,18 10,25 14,22" fill="url(#rocketGrad)" stroke="#333" stroke-width="1"/>
            <polygon points="20,18 22,25 18,22" fill="url(#rocketGrad)" stroke="#333" stroke-width="1"/>
            
            <!-- Window -->
            <circle cx="16" cy="12" r="2" fill="#87ceeb" stroke="#333" stroke-width="1"/>
            <circle cx="16" cy="12" r="1" fill="#ffffff"/>
            
            <!-- Flames -->
            <polygon points="13,22 11,28 16,26 21,28 19,22" fill="url(#flameGrad)" stroke="#ff3300" stroke-width="1"/>
            
            <!-- Stars for space theme -->
            <circle cx="6" cy="8" r="1" fill="#ffff00"/>
            <circle cx="26" cy="10" r="1" fill="#ffff00"/>
            <circle cx="8" cy="22" r="1" fill="#ffff00"/>
            <circle cx="24" cy="24" r="1" fill="#ffff00"/>
        </svg>'''
    
    def get_file_size(self, file_path):
        """Get human-readable file size."""
        try:
            size = os.path.getsize(file_path)
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024:
                    return f"{size:.1f} {unit}"
                size /= 1024
            return f"{size:.1f} TB"
        except:
            return ""
    
    def get_modified_time(self, file_path):
        """Get formatted modification time."""
        try:
            mtime = os.path.getmtime(file_path)
            return datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')
        except:
            return ""
    
    def generate_directory_html(self, current_path, items):
        """Generate HTML for directory listing."""
        # Create breadcrumb navigation
        breadcrumbs = []
        if current_path == '/':
            breadcrumbs = [('Home', '/')]
        else:
            breadcrumbs = [('Home', '/')]
            parts = current_path.strip('/').split('/')
            for i, part in enumerate(parts):
                path = '/' + '/'.join(parts[:i+1])
                breadcrumbs.append((part, path))
        
        breadcrumb_html = ' / '.join([f'<a href="{url}">{name}</a>' for name, url in breadcrumbs])
        
        # Generate file list
        items_html = []
        for item in items:
            if item['type'] == 'parent':
                icon = '📁'
                # Make directory name clickable
                name_html = f'<a href="{item["url"]}" class="dir-link">{html.escape(item["name"])}</a>'
                actions = ''  # No action buttons for parent directory
                # Parent directory row
                items_html.append(f'''
                    <tr class="directory-row" data-dir-path=".." ondrop="dropFile(event)" ondragover="allowDrop(event)" ondragleave="dragLeave(event)">
                        <td class="icon">{icon}</td>
                        <td class="name">{name_html}</td>
                        <td class="size">{item["size"]}</td>
                        <td class="modified">{item["modified"]}</td>
                        <td class="actions">{actions}</td>
                    </tr>
                ''')
            elif item['type'] == 'directory':
                icon = '📁'
                # Make directory name clickable
                name_html = f'<a href="{item["url"]}" class="dir-link">{html.escape(item["name"])}</a>'
                
                # Add action buttons for directories (rename and delete)
                current_path_param = urllib.parse.quote(current_path.lstrip('/'))
                actions_list = []
                
                # Download as zip icon
                zip_icon = f'<a href="/api/zip?dir={urllib.parse.quote(item["name"])}&path={current_path_param}" class="action-icon zip-icon" title="Download as ZIP">📦</a>'
                actions_list.append(zip_icon)
                
                # Rename icon
                rename_icon = f'<a href="#" onclick="renameItem(\'{urllib.parse.quote(item["name"])}\', \'{current_path_param}\')" class="action-icon rename-icon" title="Rename">🏷️</a>'
                actions_list.append(rename_icon)
                
                # Delete icon (for empty directories)
                delete_icon = f'<a href="#" onclick="confirmDeleteDirectory(\'{urllib.parse.quote(item["name"])}\', \'{current_path_param}\')" class="action-icon delete-icon" title="Delete (empty only)">🗑️</a>'
                actions_list.append(delete_icon)
                
                actions = ' '.join(actions_list)
                
                # Directory row with drop zone
                dir_path = urllib.parse.quote(item["name"])
                items_html.append(f'''
                    <tr class="directory-row" data-dir-path="{dir_path}" ondrop="dropFile(event)" ondragover="allowDrop(event)" ondragleave="dragLeave(event)">
                        <td class="icon">{icon}</td>
                        <td class="name">{name_html}</td>
                        <td class="size">{item["size"]}</td>
                        <td class="modified">{item["modified"]}</td>
                        <td class="actions">{actions}</td>
                    </tr>
                ''')
            else:
                # File
                icon = self.get_file_icon(item.get('mime_type', ''))
                # File name (no preview icon in name column anymore)
                file_name = html.escape(item["name"])
                name_html = file_name
                
                # Icon-based action buttons for files
                current_path_param = urllib.parse.quote(current_path.lstrip('/'))
                actions_list = []
                
                # Preview icon (if file is previewable)
                if self.is_previewable(item['name'], item.get('mime_type', '')):
                    preview_icon = f'<a href="/api/preview?file={urllib.parse.quote(item["name"])}&path={current_path_param}" class="action-icon preview-icon" target="_blank" title="Preview">👁️</a>'
                    actions_list.append(preview_icon)
                
                # Download icon
                download_icon = f'<a href="/api/download?file={urllib.parse.quote(item["name"])}&path={current_path_param}" class="action-icon download-icon" title="Download">⬇️</a>'
                actions_list.append(download_icon)
                
                # Rename icon
                rename_icon = f'<a href="#" onclick="renameItem(\'{urllib.parse.quote(item["name"])}\', \'{current_path_param}\')" class="action-icon rename-icon" title="Rename">🏷️</a>'
                actions_list.append(rename_icon)
                
                # Delete icon
                delete_icon = f'<a href="#" onclick="confirmDelete(\'{urllib.parse.quote(item["name"])}\', \'{current_path_param}\')" class="action-icon delete-icon" title="Delete">🗑️</a>'
                actions_list.append(delete_icon)
                
                actions = ' '.join(actions_list)
                
                # File row with drag capability
                file_encoded = urllib.parse.quote(item["name"])
                items_html.append(f'''
                    <tr class="file-row" draggable="true" data-file-name="{file_encoded}" ondragstart="dragStart(event)">
                        <td class="icon">{icon}</td>
                        <td class="name">{name_html}</td>
                        <td class="size">{item["size"]}</td>
                        <td class="modified">{item["modified"]}</td>
                        <td class="actions">{actions}</td>
                    </tr>
                ''')
        
        # Generate upload form
        upload_action = f'/api/upload?dir={urllib.parse.quote(current_path.lstrip("/"))}'
        upload_form = f'''
        <div class="upload-section">
            <div class="upload-toggle">
                <button type="button" id="toggleUpload" class="action-btn upload-toggle-btn">📤 Upload Files</button>
                <button type="button" id="newFolderBtn" class="action-btn new-folder-btn">📁 New Folder</button>
            </div>
            <div class="upload-container" id="uploadContainer" style="display: none;">
                <h3>📤 Upload Files</h3>
                <form id="uploadForm" action="{upload_action}" method="post" enctype="multipart/form-data">
                    <div class="upload-area" id="uploadArea">
                        <div class="upload-content">
                            <div class="upload-icon">📁</div>
                            <p class="upload-text">Click here to select files or drag and drop files</p>
                            <p class="upload-hint">支持多文件上传</p>
                            <input type="file" id="fileInput" name="files" multiple hidden>
                        </div>
                        <div class="file-list-preview" id="fileListPreview" style="display: none;">
                            <h4>Selected Files:</h4>
                            <ul id="selectedFilesList"></ul>
                        </div>
                    </div>
                    <div class="upload-controls">
                        <button type="button" id="selectBtn" class="action-btn">Select Files</button>
                        <button type="submit" id="uploadBtn" class="action-btn upload" disabled>Upload</button>
                        <button type="button" id="cancelBtn" class="action-btn cancel">Cancel</button>
                        <span id="fileCount" class="file-count"></span>
                    </div>
                </form>
            </div>
        </div>
        '''
        
        return f'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QuickServer - {html.escape(current_path)}</title>
    <link rel="icon" type="image/png" sizes="32x32" href="/favicon.ico?v={datetime.datetime.now().timestamp()}">
    <link rel="icon" type="image/png" sizes="16x16" href="/favicon.ico?v={datetime.datetime.now().timestamp()}">
    <link rel="shortcut icon" href="/favicon.ico?v={datetime.datetime.now().timestamp()}">
    <link rel="apple-touch-icon" sizes="32x32" href="/favicon.ico?v={datetime.datetime.now().timestamp()}">
    <meta name="msapplication-TileImage" content="/favicon.ico?v={datetime.datetime.now().timestamp()}">
    <link rel="stylesheet" href="/static/style.css">
    <!-- Highlight.js CSS -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css">
    <style>
        .code-preview {{
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 6px;
            overflow: hidden;
        }}
        .code-header {{
            background: #e9ecef;
            padding: 10px 15px;
            border-bottom: 1px solid #dee2e6;
            font-size: 0.9em;
            color: #495057;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .language-tag {{
            background: #6f42c1;
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            text-transform: uppercase;
        }}
        .code-content {{
            max-height: 70vh;
            overflow: auto;
        }}
        .code-content pre {{
            margin: 0;
            padding: 20px;
        }}
        .code-content code {{
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 14px;
            line-height: 1.4;
        }}
        .copy-btn {{
            background: #28a745;
            color: white;
            border: none;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            cursor: pointer;
            transition: background 0.3s;
        }}
        .copy-btn:hover {{
            background: #218838;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🚀 QuickServer</h1>
            <nav class="breadcrumb">
                {breadcrumb_html}
            </nav>
            <div class="search-section">
                <div class="search-box">
                    <input type="text" id="searchInput" placeholder="🔍 Search files and folders..." />
                    <button type="button" id="clearSearch" class="search-clear-btn" style="display: none;">✖</button>
                </div>
            </div>
        </header>
        
        <main>
            {upload_form}
            
            <table class="file-list">
                <thead>
                    <tr>
                        <th></th>
                        <th>Name</th>
                        <th>Size</th>
                        <th>Modified</th>
                        <th style="text-align: right;">Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(items_html)}
                </tbody>
            </table>
        </main>
        
        <footer style="text-align: center; margin-top: 20px; color: rgba(0, 0, 0, 0.6); font-size: 0.9em;">
            <p>QuickServer v0.1.0 - 💻 Created by <a href="https://github.com/xyanmi" target="_blank" style="color: #3498db; text-decoration: none;">@xyanmi</a></p>
        </footer>
    </div>
    
    <script>
        const fileInput = document.getElementById('fileInput');
        const uploadArea = document.getElementById('uploadArea');
        const selectBtn = document.getElementById('selectBtn');
        const uploadBtn = document.getElementById('uploadBtn');
        const cancelBtn = document.getElementById('cancelBtn');
        const fileCount = document.getElementById('fileCount');
        const uploadForm = document.getElementById('uploadForm');
        const toggleUpload = document.getElementById('toggleUpload');
        const uploadContainer = document.getElementById('uploadContainer');
        const fileListPreview = document.getElementById('fileListPreview');
        const selectedFilesList = document.getElementById('selectedFilesList');
        
        // New folder functionality
        const newFolderBtn = document.getElementById('newFolderBtn');
        
        newFolderBtn.addEventListener('click', function() {{
            const folderName = prompt('Enter folder name:');
            if (folderName && folderName.trim()) {{
                createNewFolder(folderName.trim());
            }}
        }});
        
        function createNewFolder(folderName) {{
            const url = '/api/mkdir?dir=' + encodeURIComponent(folderName) + '&path=' + encodeURIComponent('{current_path.lstrip("/")}');
            
            fetch(url)
                .then(response => response.json())
                .then(data => {{
                    if (data.success) {{
                        // Refresh the page to show the new folder
                        window.location.reload();
                    }} else {{
                        alert('Error creating folder: ' + data.message);
                    }}
                }})
                .catch(error => {{
                    console.error('Error:', error);
                    alert('Error creating folder: ' + error.message);
                }});
        }}
        
        // Search functionality
        const searchInput = document.getElementById('searchInput');
        const clearSearchBtn = document.getElementById('clearSearch');
        const fileTable = document.querySelector('.file-list tbody');
        let allRows = [];
        
        // Store all rows for filtering
        window.addEventListener('DOMContentLoaded', function() {{
            allRows = Array.from(fileTable.querySelectorAll('tr'));
        }});
        
        // Initialize immediately as well
        allRows = Array.from(fileTable.querySelectorAll('tr'));
        
        searchInput.addEventListener('input', function() {{
            const searchTerm = this.value.toLowerCase().trim();
            
            if (searchTerm === '') {{
                // Show all rows
                allRows.forEach(row => {{
                    row.style.display = '';
                }});
                clearSearchBtn.style.display = 'none';
            }} else {{
                // Filter rows
                let visibleCount = 0;
                allRows.forEach(row => {{
                    const nameCell = row.querySelector('.name');
                    if (nameCell) {{
                        const fileName = nameCell.textContent.toLowerCase();
                        if (fileName.includes(searchTerm)) {{
                            row.style.display = '';
                            visibleCount++;
                        }} else {{
                            row.style.display = 'none';
                        }}
                    }}
                }});
                clearSearchBtn.style.display = 'inline-block';
            }}
        }});
        
        clearSearchBtn.addEventListener('click', function() {{
            searchInput.value = '';
            allRows.forEach(row => {{
                row.style.display = '';
            }});
            clearSearchBtn.style.display = 'none';
            searchInput.focus();
        }});
        
        // Toggle upload area
        toggleUpload.addEventListener('click', function() {{
            if (uploadContainer.style.display === 'none') {{
                uploadContainer.style.display = 'block';
                toggleUpload.textContent = '🔼 Hide Upload';
                toggleUpload.classList.add('active');
            }} else {{
                hideUploadArea();
            }}
        }});
        
        // Cancel upload
        cancelBtn.addEventListener('click', function() {{
            hideUploadArea();
            resetUploadForm();
        }});
        
        function hideUploadArea() {{
            uploadContainer.style.display = 'none';
            toggleUpload.textContent = '📤 Upload Files';
            toggleUpload.classList.remove('active');
        }}
        
        function updateFileCount() {{
            const count = fileInput.files.length;
            if (count > 0) {{
                // Show file list
                fileListPreview.style.display = 'block';
                selectedFilesList.innerHTML = '';
                
                // Add each file to the list
                for (let i = 0; i < fileInput.files.length; i++) {{
                    const file = fileInput.files[i];
                    const li = document.createElement('li');
                    li.innerHTML = '<span class="file-name">' + file.name + '</span><span class="file-size">' + formatFileSize(file.size) + '</span>';
                    selectedFilesList.appendChild(li);
                }}
                
                // Update upload area state
                uploadArea.querySelector('.upload-content').style.display = 'none';
                fileCount.textContent = count + ' file' + (count > 1 ? 's' : '') + ' selected';
                uploadBtn.disabled = false;
                uploadArea.classList.add('has-files');
            }} else {{
                // Hide file list and show default content
                fileListPreview.style.display = 'none';
                uploadArea.querySelector('.upload-content').style.display = 'block';
                fileCount.textContent = '';
                uploadBtn.disabled = true;
                uploadArea.classList.remove('has-files');
            }}
        }}
        
        function formatFileSize(bytes) {{
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }}
        
        function resetUploadForm() {{
            fileInput.value = '';
            updateFileCount();
            uploadArea.classList.remove('has-files');
            uploadArea.querySelector('.upload-content').style.display = 'block';
            fileListPreview.style.display = 'none';
        }}
        
        // File selection
        selectBtn.addEventListener('click', function() {{ fileInput.click(); }});
        uploadArea.addEventListener('click', function() {{ fileInput.click(); }});
        
        // File input change
        fileInput.addEventListener('change', updateFileCount);
        
        // Drag and drop
        uploadArea.addEventListener('dragover', function(e) {{
            e.preventDefault();
            uploadArea.classList.add('drag-over');
        }});
        
        uploadArea.addEventListener('dragleave', function() {{
            uploadArea.classList.remove('drag-over');
        }});
        
        uploadArea.addEventListener('drop', function(e) {{
            e.preventDefault();
            uploadArea.classList.remove('drag-over');
            fileInput.files = e.dataTransfer.files;
            updateFileCount();
        }});
        
        // Form submission
        uploadForm.addEventListener('submit', function(e) {{
            if (fileInput.files.length === 0) {{
                e.preventDefault();
                alert('Please select files to upload');
                return;
            }}
            
            uploadBtn.textContent = 'Uploading...';
            uploadBtn.disabled = true;
        }});
        
        // Delete file confirmation
        function confirmDelete(fileName, currentPath) {{
            if (confirm('Are you sure you want to delete "' + decodeURIComponent(fileName) + '"?')) {{
                deleteItem(fileName, currentPath);
            }}
        }}
        
        // Delete directory confirmation
        function confirmDeleteDirectory(dirName, currentPath) {{
            const decodedDirName = decodeURIComponent(dirName);
            if (confirm('Are you sure you want to delete the directory "' + decodedDirName + '"?\\n\\nNote: Only empty directories can be deleted.')) {{
                deleteItem(dirName, currentPath);
            }}
        }}
        
        // Generic delete function using AJAX
        function deleteItem(itemName, currentPath) {{
            const url = '/api/delete?file=' + itemName + '&path=' + encodeURIComponent(currentPath);
            
            fetch(url)
                .then(response => response.json())
                .then(data => {{
                    if (data.success) {{
                        // Just refresh the page to show the updated file list, no alert needed
                        window.location.reload();
                    }} else {{
                        // Show error message
                        alert('Error: ' + data.message);
                    }}
                }})
                .catch(error => {{
                    console.error('Error:', error);
                    alert('Error deleting item: ' + error.message);
                }});
        }}
        
        // Rename item function
        function renameItem(fileName, currentPath) {{
            const decodedFileName = decodeURIComponent(fileName);
            const newName = prompt('Enter new name for "' + decodedFileName + '":', decodedFileName);
            
            if (newName && newName.trim() && newName.trim() !== decodedFileName) {{
                const url = '/api/rename?file=' + fileName + '&new_name=' + encodeURIComponent(newName.trim()) + '&path=' + encodeURIComponent(currentPath);
                
                fetch(url)
                    .then(response => response.json())
                    .then(data => {{
                        if (data.success) {{
                            // Refresh the page to show the updated file list
                            window.location.reload();
                        }} else {{
                            alert('Error renaming: ' + data.message);
                        }}
                    }})
                    .catch(error => {{
                        console.error('Error:', error);
                        alert('Error renaming: ' + error.message);
                    }});
            }}
        }}
        
        // File drag and drop functionality
        let draggedFile = null;
        const currentPath = '{current_path.lstrip("/")}';
        
        function dragStart(event) {{
            draggedFile = event.target.dataset.fileName;
            event.target.style.opacity = '0.5';
            console.log('Started dragging file:', draggedFile);
        }}
        
        function allowDrop(event) {{
            event.preventDefault();
            event.currentTarget.classList.add('drag-over');
        }}
        
        function dragLeave(event) {{
            event.currentTarget.classList.remove('drag-over');
        }}
        
        function dropFile(event) {{
            event.preventDefault();
            event.currentTarget.classList.remove('drag-over');
            
            if (!draggedFile) {{
                return;
            }}
            
            const targetDir = event.currentTarget.dataset.dirPath;
            console.log('Dropping file:', draggedFile, 'to directory:', targetDir);
            
            // Confirm the move
            const decodedFileName = decodeURIComponent(draggedFile);
            const decodedTargetDir = decodeURIComponent(targetDir);
            const targetDirName = targetDir === '..' ? 'parent directory' : decodedTargetDir;
            
            if (confirm('Move "' + decodedFileName + '" to ' + targetDirName + '?')) {{
                moveFile(draggedFile, targetDir);
            }}
            
            // Reset dragged file opacity
            const draggedElement = document.querySelector(`[data-file-name="${{draggedFile}}"]`);
            if (draggedElement) {{
                draggedElement.style.opacity = '1';
            }}
            draggedFile = null;
        }}
        
        function moveFile(fileName, targetDir) {{
            // Construct the move URL with proper encoding
            let url = '/api/move?file=' + fileName + '&target_dir=' + encodeURIComponent(targetDir) + '&path=' + encodeURIComponent(currentPath);
            
            fetch(url)
                .then(response => response.json())
                .then(data => {{
                    if (data.success) {{
                        // Refresh the page to show the updated file list
                        window.location.reload();
                    }} else {{
                        alert('Error moving file: ' + data.message);
                    }}
                }})
                .catch(error => {{
                    console.error('Error:', error);
                    alert('Error moving file: ' + error.message);
                }});
        }}
        
        // Handle drag end event to reset opacity
        document.addEventListener('dragend', function(event) {{
            if (event.target.classList.contains('file-row')) {{
                event.target.style.opacity = '1';
            }}
        }});
    </script>
</body>
</html>
        '''
    
    def generate_text_preview_html(self, file_name, content):
        """Generate HTML for text file preview."""
        # Detect file extension for language highlighting
        _, ext = os.path.splitext(file_name.lower())
        
        # Map file extensions to highlight.js language classes
        language_map = {
            # Python
            '.py': 'python',
            '.pyw': 'python',
            
            # JavaScript/TypeScript
            '.js': 'javascript', 
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            
            # Data formats
            '.json': 'json',
            '.xml': 'xml',
            '.xsl': 'xml',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.csv': 'csv',
            '.tsv': 'csv',
            '.toml': 'toml',
            
            # Web technologies
            '.html': 'html',
            '.htm': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.sass': 'sass',
            '.less': 'less',
            '.svg': 'xml',
            
            # Markup and documentation
            '.md': 'markdown',
            '.markdown': 'markdown',
            '.tex': 'latex',
            '.latex': 'latex',
            '.rtf': 'rtf',
            
            # Shell and scripts
            '.sh': 'bash',
            '.bash': 'bash',
            '.zsh': 'bash',
            '.fish': 'bash',
            '.bat': 'batch',
            '.cmd': 'batch',
            '.ps1': 'powershell',
            
            # System programming
            '.c': 'c',
            '.h': 'c',
            '.cpp': 'cpp',
            '.cxx': 'cpp',
            '.cc': 'cpp',
            '.hpp': 'cpp',
            '.hxx': 'cpp',
            '.cs': 'csharp',
            '.rs': 'rust',
            '.go': 'go',
            
            # Other programming languages
            '.java': 'java',
            '.php': 'php',
            '.phtml': 'php',
            '.rb': 'ruby',
            '.rbw': 'ruby',
            '.pl': 'perl',
            '.pm': 'perl',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.kts': 'kotlin',
            '.scala': 'scala',
            '.clj': 'clojure',
            '.cljs': 'clojure',
            '.hs': 'haskell',
            '.elm': 'elm',
            '.lua': 'lua',
            '.r': 'r',
            '.R': 'r',
            '.m': 'objectivec',
            '.vim': 'vim',
            
            # Database and query
            '.sql': 'sql',
            
            # Configuration files
            '.ini': 'ini',
            '.cfg': 'ini',
            '.conf': 'apache',
            '.env': 'bash',
            '.properties': 'properties',
            '.gitignore': 'gitignore',
            '.gitattributes': 'gitattributes',
            '.editorconfig': 'editorconfig',
            '.dockerfile': 'dockerfile',
            '.containerfile': 'dockerfile',
            
            # Log and text files
            '.log': 'accesslog',
            '.txt': 'plaintext',
            '.text': 'plaintext',
            
            # Feed formats
            '.rss': 'xml',
            '.atom': 'xml',
        }
        
        language = language_map.get(ext, 'plaintext')
        
        return f'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Preview: {html.escape(file_name)}</title>
    <link rel="icon" type="image/png" sizes="32x32" href="/favicon.ico?v={datetime.datetime.now().timestamp()}">
    <link rel="icon" type="image/png" sizes="16x16" href="/favicon.ico?v={datetime.datetime.now().timestamp()}">
    <link rel="shortcut icon" href="/favicon.ico?v={datetime.datetime.now().timestamp()}">
    <link rel="apple-touch-icon" sizes="32x32" href="/favicon.ico?v={datetime.datetime.now().timestamp()}">
    <meta name="msapplication-TileImage" content="/favicon.ico?v={datetime.datetime.now().timestamp()}">
    <link rel="stylesheet" href="/static/style.css">
    <!-- Highlight.js CSS -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css">
    <style>
        .code-preview {{
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 6px;
            overflow: hidden;
        }}
        .code-header {{
            background: #e9ecef;
            padding: 10px 15px;
            border-bottom: 1px solid #dee2e6;
            font-size: 0.9em;
            color: #495057;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .language-tag {{
            background: #6f42c1;
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            text-transform: uppercase;
        }}
        .code-content {{
            max-height: 70vh;
            overflow: auto;
        }}
        .code-content pre {{
            margin: 0;
            padding: 20px;
        }}
        .code-content code {{
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 14px;
            line-height: 1.4;
        }}
        .copy-btn {{
            background: #28a745;
            color: white;
            border: none;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            cursor: pointer;
            transition: background 0.3s;
        }}
        .copy-btn:hover {{
            background: #218838;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📄 File Preview</h1>
            <h2>{html.escape(file_name)}</h2>
            <div class="preview-actions">
                <button onclick="history.back()" class="action-btn">← Back</button>
                <a href="/api/download?file={urllib.parse.quote(file_name)}" class="action-btn download">Download</a>
            </div>
        </header>
        
        <main>
            <div class="code-preview">
                <div class="code-header">
                    <div>
                        <span>Language: </span>
                        <span class="language-tag">{language}</span>
                    </div>
                    <button class="copy-btn" onclick="copyCode()">📋 Copy</button>
                </div>
                <div class="code-content">
                    <pre><code class="language-{language}" id="code-content">{html.escape(content)}</code></pre>
                </div>
            </div>
        </main>
    </div>
    
    <!-- Highlight.js JavaScript -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <script>
        // Initialize syntax highlighting
        hljs.highlightAll();
        
        // Copy code to clipboard
        function copyCode() {{
            const codeElement = document.getElementById('code-content');
            const text = codeElement.textContent;
            
            navigator.clipboard.writeText(text).then(function() {{
                const copyBtn = document.querySelector('.copy-btn');
                const originalText = copyBtn.textContent;
                copyBtn.textContent = '✅ Copied!';
                copyBtn.style.background = '#28a745';
                
                setTimeout(function() {{
                    copyBtn.textContent = originalText;
                    copyBtn.style.background = '#28a745';
                }}, 2000);
            }}).catch(function(err) {{
                alert('Failed to copy code: ' + err);
            }});
        }}
    </script>
    
    <footer style="text-align: center; margin-top: 20px; color: rgba(255, 255, 255, 0.8); font-size: 0.9em;">
        <p>QuickServer v0.1.0 - 💻 Created by <a href="https://github.com/xyanmi" target="_blank" style="color: rgba(255, 255, 255, 0.9); text-decoration: none;">@xyanmi</a></p>
    </footer>
</body>
</html>
        '''
    
    def generate_upload_error_html(self, error_message):
        """Generate HTML for upload error."""
        return f'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Upload Error - QuickServer</title>
    <link rel="icon" type="image/png" sizes="32x32" href="/favicon.ico?v={datetime.datetime.now().timestamp()}">
    <link rel="icon" type="image/png" sizes="16x16" href="/favicon.ico?v={datetime.datetime.now().timestamp()}">
    <link rel="shortcut icon" href="/favicon.ico?v={datetime.datetime.now().timestamp()}">
    <link rel="apple-touch-icon" sizes="32x32" href="/favicon.ico?v={datetime.datetime.now().timestamp()}">
    <meta name="msapplication-TileImage" content="/favicon.ico?v={datetime.datetime.now().timestamp()}">
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>❌ Upload Error</h1>
        </header>
        
        <main>
            <div class="upload-result error">
                <h2>Upload failed</h2>
                <p class="error-message">{html.escape(error_message)}</p>
                <div class="upload-actions">
                    <button onclick="history.back()" class="action-btn">← Go Back</button>
                </div>
            </div>
        </main>
    </div>
    
    <footer style="text-align: center; margin-top: 20px; color: rgba(0, 0, 0, 0.6); font-size: 0.9em;">
        <p>QuickServer v0.1.0 - 💻 Created by <a href="https://github.com/xyanmi" target="_blank" style="color: #3498db; text-decoration: none;">@xyanmi</a></p>
    </footer>
</body>
</html>
        '''
    
    def generate_upload_success_html(self, uploaded_files, target_dir):
        """Generate HTML for successful upload."""
        files_list = ''.join([f'<li>✅ {html.escape(filename)}</li>' for filename in uploaded_files])
        return_path = '/' + target_dir if target_dir else '/'
        
        return f'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Upload Successful - QuickServer</title>
    <link rel="icon" type="image/png" sizes="32x32" href="/favicon.ico?v={datetime.datetime.now().timestamp()}">
    <link rel="icon" type="image/png" sizes="16x16" href="/favicon.ico?v={datetime.datetime.now().timestamp()}">
    <link rel="shortcut icon" href="/favicon.ico?v={datetime.datetime.now().timestamp()}">
    <link rel="apple-touch-icon" sizes="32x32" href="/favicon.ico?v={datetime.datetime.now().timestamp()}">
    <meta name="msapplication-TileImage" content="/favicon.ico?v={datetime.datetime.now().timestamp()}">
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>📤 Upload Successful</h1>
        </header>
        
        <main>
            <div class="upload-result success">
                <h2>Files uploaded successfully!</h2>
                <ul class="uploaded-files">
                    {files_list}
                </ul>
                <div class="upload-actions">
                    <a href="{return_path}" class="action-btn">← Back to Directory</a>
                </div>
            </div>
        </main>
    </div>
    
    <footer style="text-align: center; margin-top: 20px; color: rgba(0, 0, 0, 0.6); font-size: 0.9em;">
        <p>QuickServer v0.1.0 - 💻 Created by <a href="https://github.com/xyanmi" target="_blank" style="color: #3498db; text-decoration: none;">@xyanmi</a></p>
    </footer>
</body>
</html>
        '''
    
    def get_file_icon(self, mime_type):
        """Get emoji icon for file type."""
        if not mime_type:
            return '📄'
        
        if mime_type.startswith('image/'):
            return '🖼️'
        elif mime_type.startswith('video/'):
            return '🎥'
        elif mime_type.startswith('audio/'):
            return '🎵'
        elif mime_type.startswith('text/'):
            return '📝'
        elif 'pdf' in mime_type:
            return '📕'
        elif 'zip' in mime_type or 'archive' in mime_type:
            return '📦'
        else:
            return '📄'
    
    def is_previewable(self, file_name, mime_type):
        """Check if file can be previewed."""
        if mime_type and mime_type.startswith('image/'):
            return True
        
        # PDF files are previewable
        if mime_type and 'pdf' in mime_type.lower():
            return True
        
        # Also check file extension for PDF
        _, ext = os.path.splitext(file_name.lower())
        if ext == '.pdf':
            return True
        
        # Define the same text file extensions as in handle_preview
        text_extensions = {
            # Programming languages
            '.py', '.pyw',           # Python
            '.js', '.jsx', '.ts', '.tsx',  # JavaScript/TypeScript
            '.json',                 # JSON
            '.html', '.htm',         # HTML
            '.css', '.scss', '.sass', '.less',  # CSS and preprocessors
            '.xml', '.xsl',          # XML
            '.yaml', '.yml',         # YAML
            '.md', '.markdown',      # Markdown
            '.txt', '.text',         # Plain text
            '.ini', '.cfg', '.conf', # Configuration files
            '.env',                  # Environment files
            
            # Shell and batch scripts
            '.sh', '.bash', '.zsh', '.fish',  # Shell scripts
            '.bat', '.cmd',          # Windows batch
            '.ps1',                  # PowerShell
            
            # System programming
            '.c', '.h',              # C
            '.cpp', '.cxx', '.cc', '.hpp', '.hxx',  # C++
            '.cs',                   # C#
            '.rs',                   # Rust
            '.go',                   # Go
            
            # Other languages
            '.java',                 # Java
            '.php', '.phtml',        # PHP
            '.rb', '.rbw',           # Ruby
            '.pl', '.pm',            # Perl
            '.swift',                # Swift
            '.kt', '.kts',           # Kotlin
            '.scala',                # Scala
            '.clj', '.cljs',         # Clojure
            '.hs',                   # Haskell
            '.elm',                  # Elm
            '.lua',                  # Lua
            '.r', '.R',              # R
            '.m',                    # Objective-C / MATLAB
            '.vim',                  # Vim script
            '.dockerfile', '.containerfile',  # Docker
            
            # Data and config formats
            '.sql',                  # SQL
            '.csv', '.tsv',          # CSV/TSV
            '.log',                  # Log files
            '.properties',           # Properties files
            '.toml',                 # TOML
            '.gitignore', '.gitattributes',  # Git files
            '.editorconfig',         # Editor config
            
            # Web and markup
            '.svg',                  # SVG (text-based)
            '.rss', '.atom',         # Feed formats
            '.tex', '.latex',        # LaTeX
            '.rtf',                  # Rich Text Format
        }
        
        return ext in text_extensions or (mime_type and mime_type.startswith('text/'))
    
    def get_css_content(self):
        """Return CSS content for styling."""
        return '''
/* QuickServer CSS Styles */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: #333;
    min-height: 100vh;
    line-height: 1.6;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
}

header {
    background: rgba(255, 255, 255, 0.95);
    padding: 20px;
    border-radius: 10px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    margin-bottom: 20px;
    backdrop-filter: blur(10px);
}

header h1 {
    color: #2c3e50;
    margin-bottom: 10px;
    font-size: 2.5em;
    text-align: center;
}

header h2 {
    color: #34495e;
    font-size: 1.2em;
    margin-bottom: 10px;
}

.breadcrumb {
    font-size: 1.1em;
    color: #7f8c8d;
    text-align: center;
}

.breadcrumb a {
    color: #3498db;
    text-decoration: none;
    transition: color 0.3s;
}

.breadcrumb a:hover {
    color: #2980b9;
    text-decoration: underline;
}

.search-section {
    margin-top: 15px;
}

.search-box {
    position: relative;
    max-width: 400px;
    margin: 0 auto;
}

.search-box input {
    width: 100%;
    padding: 8px 12px;
    padding-right: 35px;
    border: 2px solid #ddd;
    border-radius: 20px;
    font-size: 0.9em;
    outline: none;
    transition: all 0.3s ease;
}

.search-box input:focus {
    border-color: #3498db;
    box-shadow: 0 0 5px rgba(52, 152, 219, 0.3);
}

.search-clear-btn {
    position: absolute;
    right: 8px;
    top: 50%;
    transform: translateY(-50%);
    background: none;
    border: none;
    font-size: 0.8em;
    color: #999;
    cursor: pointer;
    padding: 2px;
    border-radius: 50%;
    transition: all 0.3s ease;
}

.search-clear-btn:hover {
    background: #f0f0f0;
    color: #666;
}

.preview-actions {
    text-align: center;
    margin-top: 15px;
}

main {
    flex: 1;
    background: rgba(255, 255, 255, 0.95);
    border-radius: 10px;
    padding: 20px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    backdrop-filter: blur(10px);
}

/* Upload Section Styles */
.upload-section {
    margin-bottom: 20px;
}

.upload-toggle {
    text-align: center;
    margin-bottom: 10px;
}

.upload-toggle-btn {
    background: #3498db;
    font-size: 1em;
    padding: 10px 20px;
    transition: all 0.3s ease;
    margin-right: 10px;
}

.upload-toggle-btn:hover {
    background: #2980b9;
    transform: translateY(-1px);
}

.upload-toggle-btn.active {
    background: #e74c3c;
}

.upload-toggle-btn.active:hover {
    background: #c0392b;
}

.new-folder-btn {
    background: #27ae60;
    font-size: 1em;
    padding: 10px 20px;
    transition: all 0.3s ease;
}

.new-folder-btn:hover {
    background: #229954;
    transform: translateY(-1px);
}

.upload-container {
    padding: 20px;
    background: #f8f9fa;
    border-radius: 8px;
    border: 2px dashed #dee2e6;
    animation: slideDown 0.3s ease-out;
}

@keyframes slideDown {
    from {
        opacity: 0;
        transform: translateY(-10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.upload-container h3 {
    color: #495057;
    margin-bottom: 15px;
    text-align: center;
}

.upload-area {
    background: white;
    border: 2px dashed #ced4da;
    border-radius: 8px;
    padding: 40px 20px;
    text-align: center;
    cursor: pointer;
    transition: all 0.3s ease;
    margin-bottom: 15px;
}

.upload-area:hover {
    border-color: #3498db;
    background: #f8f9fa;
}

.upload-area.drag-over {
    border-color: #27ae60;
    background: #d4edda;
}

.upload-area.has-files {
    border-color: #27ae60;
    background: #d1ecf1;
}

.upload-content {
    pointer-events: none;
}

.upload-icon {
    font-size: 3em;
    margin-bottom: 10px;
}

.upload-text {
    font-size: 1.1em;
    color: #495057;
    margin-bottom: 5px;
}

.upload-hint {
    font-size: 0.9em;
    color: #6c757d;
}

.file-list-preview {
    margin-top: 15px;
    text-align: left;
}

.file-list-preview h4 {
    color: #495057;
    margin-bottom: 10px;
    font-size: 1em;
}

.file-list-preview ul {
    list-style: none;
    margin: 0;
    padding: 0;
    max-height: 200px;
    overflow-y: auto;
}

.file-list-preview li {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 12px;
    margin-bottom: 5px;
    background: white;
    border: 1px solid #dee2e6;
    border-radius: 4px;
    transition: background-color 0.2s;
}

.file-list-preview li:hover {
    background: #f8f9fa;
}

.file-name {
    flex: 1;
    font-weight: 500;
    color: #495057;
    margin-right: 10px;
    word-break: break-all;
}

.file-size {
    font-size: 0.85em;
    color: #6c757d;
    white-space: nowrap;
}

.upload-controls {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 15px;
    flex-wrap: wrap;
}

.file-count {
    color: #495057;
    font-weight: 500;
}

/* Upload Result Styles */
.upload-result {
    text-align: center;
    padding: 40px 20px;
}

.upload-result h2 {
    margin-bottom: 20px;
}

.upload-result.success h2 {
    color: #27ae60;
}

.upload-result.error h2 {
    color: #e74c3c;
}

.uploaded-files {
    list-style: none;
    margin-bottom: 20px;
    text-align: left;
    max-width: 500px;
    margin-left: auto;
    margin-right: auto;
}

.uploaded-files li {
    padding: 8px 0;
    border-bottom: 1px solid #dee2e6;
}

.error-message {
    color: #e74c3c;
    margin-bottom: 20px;
    font-weight: 500;
}

.upload-actions {
    margin-top: 20px;
}

.file-list {
    width: 100%;
    border-collapse: collapse;
    margin-top: 10px;
}

.file-list th {
    background: #f8f9fa;
    padding: 12px;
    text-align: left;
    border-bottom: 2px solid #dee2e6;
    font-weight: 600;
    color: #495057;
}

.file-list td {
    padding: 12px;
    border-bottom: 1px solid #dee2e6;
    vertical-align: middle;
}

.file-list tr:hover {
    background-color: #f8f9fa;
}

.icon {
    width: 40px;
    text-align: center;
    font-size: 1.2em;
}

.name {
    font-weight: 500;
    color: #2c3e50;
}

/* Directory links styling */
.dir-link {
    color: #2c3e50;
    text-decoration: none;
    font-weight: 500;
    transition: color 0.3s ease;
}

.dir-link:hover {
    color: #3498db;
    text-decoration: underline;
}

/* Preview icon styling */
.preview-icon {
    color: #27ae60;
    background: rgba(39, 174, 96, 0.1);
}

.preview-icon:hover {
    background: rgba(39, 174, 96, 0.2);
}

.zip-icon {
    color: #9b59b6;
    background: rgba(155, 89, 182, 0.1);
}

.zip-icon:hover {
    background: rgba(155, 89, 182, 0.2);
}

.rename-icon {
    color: #f39c12;
    background: rgba(243, 156, 18, 0.1);
}

.rename-icon:hover {
    background: rgba(243, 156, 18, 0.2);
}

.download-icon {
    color: #3498db;
    background: rgba(52, 152, 219, 0.1);
}

.download-icon:hover {
    background: rgba(52, 152, 219, 0.2);
}

.size {
    width: 100px;
    color: #7f8c8d;
    font-size: 0.9em;
}

.modified {
    width: 150px;
    color: #7f8c8d;
    font-size: 0.9em;
}

.actions {
    width: 200px;
    text-align: right;
}

.action-btn {
    display: inline-block;
    padding: 6px 12px;
    margin-left: 5px;
    background: #3498db;
    color: white;
    text-decoration: none;
    border-radius: 4px;
    font-size: 0.9em;
    transition: background 0.3s;
    border: none;
    cursor: pointer;
}

.action-btn:hover {
    background: #2980b9;
}

.action-btn:disabled {
    background: #95a5a6;
    cursor: not-allowed;
}

.action-btn.preview {
    background: #27ae60;
}

.action-btn.preview:hover {
    background: #229954;
}

.action-btn.download {
    background: #e74c3c;
}

.action-btn.download:hover {
    background: #c0392b;
}

.action-btn.upload {
    background: #f39c12;
}

.action-btn.upload:hover {
    background: #e67e22;
}

.action-btn.navigate {
    background: #f39c12;
}

.action-btn.navigate:hover {
    background: #d68910;
}

.action-btn.cancel {
    background: #95a5a6;
}

.action-btn.cancel:hover {
    background: #7f8c8d;
}

/* Action icon styles for download and delete */
.action-icon {
    display: inline-block;
    padding: 3px 5px;
    margin: 0 1px;
    font-size: 0.9em;
    text-decoration: none;
    border-radius: 4px;
    transition: all 0.3s ease;
    opacity: 0.8;
}

.action-icon:hover {
    opacity: 1;
    transform: scale(1.1);
    text-decoration: none;
}

.delete-icon {
    color: #e74c3c;
    background: rgba(231, 76, 60, 0.1);
}

.delete-icon:hover {
    background: rgba(231, 76, 60, 0.2);
}

.text-preview {
    background: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 6px;
    padding: 20px;
    max-height: 70vh;
    overflow: auto;
}

.text-preview pre {
    margin: 0;
    white-space: pre-wrap;
    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
    font-size: 14px;
    line-height: 1.4;
}

footer {
    text-align: center;
    margin-top: 20px;
    color: rgba(255, 255, 255, 0.8);
    font-size: 0.9em;
}

/* Drag and Drop Styles */
.file-row {
    cursor: move;
    transition: all 0.3s ease;
}

.file-row:hover {
    background-color: #f0f0f0;
}

.file-row[draggable="true"] {
    cursor: grab;
}

.file-row[draggable="true"]:active {
    cursor: grabbing;
}

.directory-row {
    transition: all 0.3s ease;
}

.directory-row.drag-over {
    background-color: #e3f2fd !important;
    border: 2px dashed #2196f3;
    transform: scale(1.02);
}

.directory-row.drag-over .icon {
    animation: bounce 0.5s ease-in-out;
}

@keyframes bounce {
    0%, 20%, 50%, 80%, 100% {
        transform: translateY(0);
    }
    40% {
        transform: translateY(-5px);
    }
    60% {
        transform: translateY(-3px);
    }
}

.file-row.dragging {
    opacity: 0.5;
    transform: rotate(2deg);
}

/* Responsive design */
@media (max-width: 768px) {
    .container {
        padding: 10px;
    }
    
    header {
        padding: 15px;
    }
    
    header h1 {
        font-size: 1.8em;
        margin-bottom: 8px;
    }
    
    .breadcrumb {
        font-size: 0.9em;
        word-break: break-all;
        line-height: 1.4;
    }
    
    /* 改进表格在移动端的显示 */
    .file-list {
        font-size: 0.85em;
    }
    
    .file-list th,
    .file-list td {
        padding: 8px 4px;
    }
    
    /* 隐藏不重要的列 */
    .size, .modified {
        display: none;
    }
    
    /* 调整图标列宽度 */
    .icon {
        width: 30px;
        font-size: 1em;
    }
    
    /* 文件名列占更多空间 */
    .name {
        width: auto;
        min-width: 120px;
    }
    
    /* 操作列紧凑显示 */
    .actions {
        width: 120px;
        text-align: center;
    }
    
    .action-icon {
        padding: 6px 8px;
        margin: 1px;
        font-size: 1em;
        display: inline-block;
    }
    
    /* 上传区域优化 */
    .upload-area {
        padding: 20px 10px;
    }
    
    .upload-icon {
        font-size: 2em;
    }
    
    .upload-text {
        font-size: 1em;
    }
    
    .upload-hint {
        font-size: 0.85em;
    }
    
    .upload-controls {
        flex-direction: column;
        gap: 8px;
    }
    
    .action-btn {
        padding: 8px 16px;
        font-size: 0.9em;
        margin: 2px 0;
    }
    
    /* 文件列表预览优化 */
    .file-list-preview {
        margin-top: 10px;
    }
    
    .file-list-preview ul {
        max-height: 150px;
    }
    
    .file-list-preview li {
        padding: 6px 8px;
        font-size: 0.85em;
    }
    
    .file-name {
        font-size: 0.9em;
    }
    
    .file-size {
        font-size: 0.8em;
    }
}

/* 专门针对手机竖屏优化 */
@media (max-width: 480px) {
    .container {
        padding: 5px;
    }
    
    header {
        padding: 10px;
        margin-bottom: 10px;
    }
    
    header h1 {
        font-size: 1.5em;
    }
    
    main {
        padding: 15px;
    }
    
    /* 面包屑导航移动端优化 */
    .breadcrumb {
        font-size: 0.8em;
        white-space: nowrap;
        overflow-x: auto;
        padding-bottom: 5px;
    }
    
    /* 表格完全重构为卡片式布局 */
    .file-list {
        border: none;
    }
    
    .file-list thead {
        display: none;
    }
    
    .file-list tbody {
        display: block;
    }
    
    .file-list tr {
        display: block;
        margin-bottom: 10px;
        padding: 10px;
        background: #f8f9fa;
        border-radius: 8px;
        border: 1px solid #dee2e6;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    .file-list tr:hover {
        background: #e9ecef;
    }
    
    .file-list td {
        display: block;
        padding: 2px 0;
        border: none;
        text-align: left;
    }
    
    .file-list td.icon {
        display: inline-block;
        width: auto;
        margin-right: 8px;
        vertical-align: middle;
    }
    
    .file-list td.name {
        display: inline-block;
        width: auto;
        vertical-align: middle;
        font-weight: 600;
        color: #2c3e50;
    }
    
    .file-list td.size,
    .file-list td.modified {
        display: inline-block;
        font-size: 0.75em;
        color: #6c757d;
        margin-right: 10px;
    }
    
    .file-list td.actions {
        display: block;
        text-align: center;
        margin-top: 8px;
        padding-top: 8px;
        border-top: 1px solid #dee2e6;
    }
    
    .action-icon {
        padding: 8px 12px;
        margin: 2px 4px;
        font-size: 1.1em;
        min-width: 40px;
        border-radius: 6px;
    }
    
    /* 上传区域进一步优化 */
    .upload-section {
        margin-bottom: 15px;
    }
    
    .upload-container {
        padding: 15px;
    }
    
    .upload-area {
        padding: 15px 8px;
        min-height: 100px;
    }
    
    .upload-icon {
        font-size: 1.8em;
    }
    
    .upload-text {
        font-size: 0.9em;
        margin-bottom: 3px;
    }
    
    .upload-hint {
        font-size: 0.75em;
    }
    
    .upload-controls {
        gap: 6px;
    }
    
    .action-btn {
        padding: 10px 20px;
        font-size: 0.9em;
        border-radius: 6px;
    }
    
    .upload-toggle-btn {
        padding: 8px 16px;
        font-size: 0.9em;
    }
    
    /* 文件计数和选择列表 */
    .file-count {
        font-size: 0.85em;
        margin-top: 5px;
    }
    
    .file-list-preview ul {
        max-height: 120px;
    }
    
    .file-list-preview li {
        padding: 5px 8px;
        font-size: 0.8em;
        margin-bottom: 3px;
    }
    
    /* 目录链接优化 */
    .dir-link {
        font-size: 1em;
        word-break: break-word;
    }
    
    /* 预览页面优化 */
    .text-preview {
        padding: 15px;
        font-size: 0.85em;
        max-height: 60vh;
    }
    
    .text-preview pre {
        font-size: 12px;
        line-height: 1.3;
        word-wrap: break-word;
        white-space: pre-wrap;
    }
    
    .preview-actions {
        margin-top: 10px;
    }
    
    .preview-actions .action-btn {
        margin: 5px;
        padding: 8px 16px;
    }
}

/* 超小屏幕优化 */
@media (max-width: 360px) {
    header h1 {
        font-size: 1.3em;
    }
    
    .action-icon {
        padding: 6px 8px;
        margin: 1px 2px;
        font-size: 1em;
    }
    
    .upload-area {
        padding: 10px 5px;
    }
    
    .file-list tr {
        padding: 8px;
    }
    
    .action-btn {
        padding: 8px 12px;
        font-size: 0.8em;
    }
}
    '''
    
    def log_message(self, format, *args):
        """Override to customize logging."""
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {format % args}")


class QuickServer:
    """Main QuickServer class."""
    
    def __init__(self, host='0.0.0.0', port=8000, directory='.'):
        self.host = host
        self.port = port
        self.directory = os.path.abspath(directory)
        self.httpd = None
        self.server_thread = None
        
    def start(self):
        """Start the server."""
        # Create handler with bound directory
        def handler_factory(*args, **kwargs):
            return QuickServerHandler(*args, directory=self.directory, **kwargs)
        
        try:
            self.httpd = HTTPServer((self.host, self.port), handler_factory)
            
            print(f"\n🚀 QuickServer starting...")
            print(f"📁 Serving directory: {self.directory}")
            print(f"💻 Created by @xyanmi (https://github.com/xyanmi)")
            print(f"🌐 Server running at:")
            print(f"   • Local:    http://localhost:{self.port}")
            print(f"   • Network:  http://{self.get_local_ip()}:{self.port}")
            print(f"\n💡 Access Tips:")
            print(f"   • Use localhost URL for immediate access")
            print(f"   • If network URL doesn't work initially, try localhost first")
            print(f"   • Windows Firewall may prompt for permission on first access")
            print(f"   • Press Ctrl+C to stop the server\n")
            
            self.httpd.serve_forever()
            
        except OSError as e:
            if e.errno == 48:  # Address already in use
                print(f"❌ Port {self.port} is already in use. Try a different port with -p <port>")
            else:
                print(f"❌ Failed to start server: {e}")
            raise
    
    def stop(self):
        """Stop the server."""
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
            print("✅ Server stopped.")
    
    def get_local_ip(self):
        """Get local IP address."""
        try:
            # Connect to a remote address to determine local IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except:
            return "127.0.0.1"
    
    def test_network_access(self):
        """Test if the server is accessible from network."""
        try:
            local_ip = self.get_local_ip()
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.settimeout(2)
            result = test_socket.connect_ex((local_ip, self.port))
            test_socket.close()
            return result == 0
        except:
            return False 